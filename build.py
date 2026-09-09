"""Dieu phoi: collector -> bo quy tac -> data/latest.json + snapshot lich su.

Chay tay:  python build.py
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml

from collectors.manual_data import load_manual
from collectors.market_data import (
    fetch_current_market_cap,
    fetch_daily_batch,
    fetch_hose_universe,
    fetch_lnst_batch,
    fetch_shares_outstanding,
)
from rules.basket import build_vn30
from rules.lich_review import ky_review_ke_tiep
from rules.models import BasketResult, StockInput
from rules.thresholds import load_thresholds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MANUAL_FILE = DATA_DIR / "manual.yaml"
PREV_BASKET_FILE = DATA_DIR / "previous_basket.json"
HOSE_INDEX_DIR = DATA_DIR / "hose_index"


def load_free_float_moi_nhat(
    hose_index_dir: Path = HOSE_INDEX_DIR, ky: str | None = None
) -> tuple[dict[str, float], str | None]:
    """Doc file data/hose_index/<ky>.yaml (sinh boi scripts/cap_nhat_cbtt.py tu cong bo
    chinh thuc HOSE) va tra ve (free_float dict, ky). Ky la chuoi "YYYY-MM" nen so sanh
    chuoi la du de tim ky moi nhat.

    Neu truyen `ky` (vd "2026-07"), doc DUNG file kỳ đó thay vì tự chọn kỳ mới nhất -
    dùng khi caller (vd bài kiểm định nghiệm thu) cần free-float ĐÚNG KỲ đang xét, để
    không bị lệch kỳ khi sau này co them file moi hon duoc them vao thu muc.

    Neu chua co file nao (vd moi clone repo, chua chay cap_nhat_cbtt.py), tra ve ({}, None)
    - moi ma se roi vao missing_data, khong duoc doan.
    """
    if ky is not None:
        p = hose_index_dir / f"{ky}.yaml"
        if not p.exists():
            return {}, None
        du_lieu = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return du_lieu.get("free_float", {}) or {}, du_lieu.get("ky")

    files = sorted(hose_index_dir.glob("*.yaml"))
    if not files:
        return {}, None

    moi_nhat = max(files, key=lambda p: p.stem)  # ten file la <ky>.yaml, "2026-01" < "2026-04" ...
    du_lieu = yaml.safe_load(moi_nhat.read_text(encoding="utf-8")) or {}
    return du_lieu.get("free_float", {}) or {}, du_lieu.get("ky")

XAP_XI = [
    "GTGD chưa gồm giao dịch thỏa thuận (nguồn dữ liệu chỉ có khớp lệnh) — "
    "turnover ratio là ước tính cận dưới.",
    "GTVH 12 tháng dùng số cổ phiếu lưu hành hiện tại cho toàn chuỗi giá quá khứ — "
    "lệch với mã có phát hành thêm hoặc chia thưởng trong kỳ.",
    "Ý kiến kiểm toán không đọc được tự động — mã chưa xác nhận hiển thị là "
    "'chưa xác nhận', không mặc định là đạt.",
    "Ngày niêm yết cho mã không có xác nhận thủ công trong data/manual.yaml được SUY "
    "từ ngày giao dịch đầu tiên trong chuỗi giá 12 tháng — cách này không phân biệt "
    "được mã mới niêm yết với mã bị tạm ngừng giao dịch dài rồi giao dịch lại trong "
    "cửa sổ dữ liệu. Cách suy này còn dùng lịch sử giá của mã trên MỌI sàn (nguồn dữ "
    "liệu không phân biệt sàn), nên với cổ phiếu CHUYỂN SÀN (ví dụ từ UPCoM sang HOSE "
    "như MCH) thời gian niêm yết trên HOSE sẽ bị tính DÀI HƠN thực tế — những mã như "
    "vậy được đối chiếu với danh mục VNAllshare của công bố HOSE gần nhất và đánh dấu "
    "cảnh báo riêng ở cấp mã nếu không có mặt trong công bố đó.",
    "Thứ hạng vốn hóa (GTVH) được tính đầy đủ trên toàn bộ sàn HOSE, nhưng các chỉ "
    "tiêu bình quân 12 tháng (GTVH, GTGD khớp lệnh, thanh khoản...) chỉ được tính "
    "cho nhóm mã đứng đầu theo vốn hóa HIỆN TẠI (xem rules/thresholds.yaml, "
    "vn30.so_ma_lay_lich_su_gia) nhằm giảm số lượt gọi dữ liệu giá lịch sử — mã "
    "ngoài nhóm này không được xét vào rổ.",
]


def suy_ngay_niem_yet(daily: pd.DataFrame, start: date) -> tuple[Optional[date], bool, Optional[str]]:
    """Suy 'da du 6 thang niem yet hay chua' tu ngay giao dich DAU TIEN trong chuoi
    gia, khi khong co listing_date xac nhan thu cong trong manual.yaml.

    Tra ve (listing_date_suy_ra, niem_yet_truoc_cua_so, niem_yet_nguon):
    - Ngay giao dich dau tien lech qua nguong dung sai ky thuat (thresholds.yaml,
      eligibility.inferred_tolerance_business_days) so voi ngay bat dau cua so yeu
      cau -> ro rang ma moi niem yet TRONG cua so -> suy ra listing_date = chinh
      ngay giao dich dau tien do.
    - Ngay giao dich dau tien trong nguong dung sai (tuc la ma da co giao dich tu
      truoc/sat ngay bat dau cua so) -> ma da niem yet it nhat bang do dai cua so
      (vd 12 thang) -> KHONG bia ngay cu the, chi danh dau niem_yet_truoc_cua_so=True.

    Neu daily rong thi khong suy duoc gi (truong hop nay build.py da loc truoc o
    lap_stock_inputs, khong con toi day).
    """
    if daily is None or daily.empty:
        return None, False, None

    ngay_dau = pd.to_datetime(daily["time"]).min().date()
    nguong_bd = load_thresholds()["eligibility"]["inferred_tolerance_business_days"]

    if ngay_dau <= start:
        lech_bd = 0
    else:
        lech_bd = int(np.busday_count(start.isoformat(), ngay_dau.isoformat()))

    if lech_bd > nguong_bd:
        return ngay_dau, False, "suy từ ngày giao dịch đầu tiên"
    return None, True, "giao dịch từ trước cửa sổ dữ liệu"


def _ghep_lnst(sym: str, m: dict, lnst_auto: dict) -> dict:
    """Ghep LNST cho 1 ma: manual.yaml (neu co khai bao lnst_positive) THANG so tu dong.

    Tra dict {lnst_positive, lnst_ty, lnst_ky, lnst_nguon} - dung ca cho logic sang loc
    (lnst_positive) lan hien thi web (lnst_ty/ky/nguon) de nguoi doc tu kiem tra duoc.
    Manual thang vi nguoi xac nhan dang tin cay hon so tu dong; nhung manual chi co
    co lnst_positive (bool) chu khong co so VND, nen lnst_ty/ky la None trong truong hop nay.
    """
    if m.get("lnst_positive") is not None:
        return {
            "lnst_positive": m["lnst_positive"],
            "lnst_ty": None,
            "lnst_ky": None,
            "lnst_nguon": "xác nhận thủ công",
        }
    auto = lnst_auto.get(sym)
    if auto is None:
        return {"lnst_positive": None, "lnst_ty": None, "lnst_ky": None, "lnst_nguon": None}
    return {
        "lnst_positive": auto["lnst_vnd"] > 0,
        "lnst_ty": round(auto["lnst_vnd"] / 1e9, 1),
        "lnst_ky": auto["ky"],
        "lnst_nguon": "tự động",
    }


def lap_stock_inputs(symbols, daily_map, shares_map, manual, previous_basket, free_float,
                      lnst_auto: dict | None = None, start: date | None = None) -> list[StockInput]:
    """Ghep so tu may (daily, SLCP, LNST tu dong) voi so nguoi xac nhan (manual) va free
    float tu cong bo chinh thuc HOSE (free_float dict, xem load_free_float_moi_nhat) thanh
    StockInput.

    free_float la nguon RIENG voi manual - HOSE cong bo moi quy cho toan bo VNAllshare,
    manual.yaml khong con giu truong nay (tranh hai nguon su that). Ma khong co trong
    cong bo HOSE (vd chua vao VNAllshare) se la None - khong doan.

    lnst_auto: dict symbol -> {lnst_vnd, ky, nguon} tu collectors.market_data.fetch_lnst_batch,
    thuong chi co cho top N ma theo GTVH (goi BCTC cho ca vu tru la khong can thiet).
    Neu manual.yaml khai bao lnst_positive cho 1 ma, gia tri do THANG so tu dong (xem _ghep_lnst).

    start: ngay bat dau cua so du lieu gia da yeu cau (tham so `start` truyen cho
    fetch_daily_batch o main()). Dung de SUY ngay niem yet tu ngay giao dich dau tien
    trong chuoi gia khi ma KHONG co listing_date xac nhan thu cong (xem suy_ngay_niem_yet).
    Neu khong truyen start (None), KHONG suy doan - giu nguyen hanh vi cu (listing_date
    chi lay tu manual.yaml, None neu khong co).

    Bo qua ma khong co SLCP hoac khong co du lieu gia (daily rong/thieu) - rules/definitions.py
    se nem ValueError neu dua daily rong vao, nen phai loc truoc o day.
    """
    lnst_auto = lnst_auto or {}
    prev = {s.upper() for s in previous_basket}
    ds: list[StockInput] = []
    for sym in symbols:
        sym = sym.upper()
        slcp = shares_map.get(sym)
        daily = daily_map.get(sym)
        if not slcp or daily is None or daily.empty:
            continue
        m = manual.get(sym, {})
        lnst = _ghep_lnst(sym, m, lnst_auto)

        listing_date = m.get("listing_date")
        niem_yet_truoc_cua_so = False
        if listing_date is not None:
            niem_yet_nguon = "xác nhận thủ công"
        elif start is not None:
            listing_date, niem_yet_truoc_cua_so, niem_yet_nguon = suy_ngay_niem_yet(daily, start)
        else:
            niem_yet_nguon = None

        # Tuyen kiem tra cheo voi cong bo VNAllshare chinh thuc cua HOSE (xem
        # rules/models.py, StockInput.canh_bao_chuyen_san): chi ap dung khi ma dat
        # dieu kien tham gia CHI nho suy luan "truoc cua so" (khong co xac nhan
        # thu cong) - neu ma khong co mat trong free_float (chinh la danh muc
        # VNAllshare da qua sang loc cua ky cong bo gan nhat, xem
        # scripts/cap_nhat_cbtt.py) thi nghi ngo vua chuyen san, phai canh bao.
        canh_bao_chuyen_san = (
            niem_yet_nguon == "giao dịch từ trước cửa sổ dữ liệu"
            and sym not in free_float
        )

        ds.append(StockInput(
            symbol=sym,
            daily=daily,
            shares_outstanding=slcp,
            listing_date=listing_date,
            niem_yet_truoc_cua_so=niem_yet_truoc_cua_so,
            free_float=free_float.get(sym),
            in_previous_basket=sym in prev,
            warning_status=m.get("warning_status", "none"),
            lnst_positive=lnst["lnst_positive"],
            audit_opinion=m.get("audit_opinion", "unknown"),
            lnst_ty=lnst["lnst_ty"],
            lnst_ky=lnst["lnst_ky"],
            lnst_nguon=lnst["lnst_nguon"],
            niem_yet_nguon=niem_yet_nguon,
            canh_bao_chuyen_san=canh_bao_chuyen_san,
        ))
    return ds


def canh_bao_ma_ro_cu_bien_mat(previous_basket: list[str], ds: list[StockInput]) -> list[str]:
    """Tuyen phong thu thu hai: neu mot ma dang trong ro VN30 KY TRUOC lai
    khong co mat trong vu tru da lap StockInput (nghia la khong lay duoc du
    lieu gia/SLCP - xem lap_stock_inputs, buoc "bo qua ma khong co SLCP hoac
    khong co du lieu gia"), gan nhu chac chan la LOI KY THUAT (mang loi, cache
    hong, API sap...) chu khong phai su that "ma nay het niem yet". Mot ma
    dang trong VN30 ma bien mat khoi du lieu can duoc canh bao TO, khong duoc
    de am tham lot qua.

    Tra ve danh sach cau canh bao tieng Viet co dau, moi cau neu dich danh 1 ma.
    """
    ma_trong_vu_tru = {si.symbol.upper() for si in ds}
    ma_bien_mat = sorted(s.upper() for s in previous_basket if s.upper() not in ma_trong_vu_tru)
    return [
        f"Mã {ma} đang ở trong rổ VN30 kỳ trước nhưng không lấy được dữ liệu giá/SLCP "
        f"kỳ này nên KHÔNG THỂ xét — nghi ngờ lỗi kỹ thuật (mạng lỗi/cache hỏng/API sập), "
        f"không phải sự thật thị trường, cần kiểm tra lại nguồn dữ liệu cho mã này."
        for ma in ma_bien_mat
    ]


def _ket_luan(symbol: str, r: BasketResult) -> str:
    if symbol in r.constituents:
        return "Trong rổ dự kiến"
    if symbol in r.reserve:
        return "Dự phòng"
    if symbol in r.missing_data:
        return "Thiếu dữ liệu"
    return "Không đạt"


def gom_lich_su(hist_dir: Path, so_ngay: int = 90) -> dict[str, list[dict]]:
    """Gom cac snapshot ngay (data/history/*.json, sinh boi main() moi lan chay) thanh
    chuoi theo ma, de trang tinh ve sparkline ma khong phai liet ke thu muc (trang tinh
    khong lam duoc viec do)."""
    if not hist_dir.exists():
        return {}
    out: dict[str, list[dict]] = {}
    for p in sorted(hist_dir.glob("*.json"))[-so_ngay:]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Bỏ qua snapshot hỏng: %s", p.name)
            continue
        for s in d.get("stocks", []):
            out.setdefault(s["symbol"], []).append({
                "ngay": d["as_of"],
                "gtvh_rank": s["gtvh_rank"],
                "gtgd_kl_ty": s["gtgd_kl_ty"],
            })
    return out


def xuat_json(r: BasketResult, as_of: date, ky_review: str, lich_su: dict | None = None) -> dict:
    top = load_thresholds()["vn30"]["consideration_list_size"]
    xep = sorted(r.metrics.items(), key=lambda kv: kv[1]["gtvh_rank"])[:top]

    stocks = []
    for sym, m in xep:
        stocks.append({
            "symbol": sym,
            "gtvh_rank": m["gtvh_rank"],
            "gtvh_ty": round(m["gtvh"] / 1e9, 1),
            "gtvh_f_ty": None if m["gtvh_f"] is None else round(m["gtvh_f"] / 1e9, 1),
            "gtgd_kl_ty": round(m["gtgd_kl"] / 1e9, 1),
            "klgd_kl": round(m["klgd_kl"]),
            "turnover": None if m["turnover"] is None else round(m["turnover"], 6),
            "free_float": m["free_float"],
            "free_float_rounded": m["free_float_rounded"],
            "in_previous_basket": m["in_previous_basket"],
            "lnst_ty": m["lnst_ty"],
            "lnst_ky": m["lnst_ky"],
            "lnst_nguon": m["lnst_nguon"],
            # Can cu ve thoi gian niem yet - de nguoi doc web tu kiem tra, khong chi thay ket luan.
            "niem_yet_nguon": m["niem_yet_nguon"],
            "niem_yet_thang": m["niem_yet_thang"],
            "ket_luan": _ket_luan(sym, r),
            # Nhan canh bao rieng cho tung ma - khong duoc am tham bo (spec muc 4.3)
            "canh_bao": (
                ([] if m["audit_opinion"] == "unqualified"
                 else ["Chưa xác nhận ý kiến kiểm toán"])
                + (["Chưa xác nhận được thời gian niêm yết trên HOSE; mã không có "
                    "trong công bố VNAllshare gần nhất nên có thể mới chuyển sàn "
                    "(vd. từ UPCoM sang HOSE) — cần xác nhận listing_date thủ công "
                    "trong data/manual.yaml"]
                   if m["canh_bao_chuyen_san"] else [])
            ),
            "screens": [
                {"step": s.step, "rule_ref": s.rule_ref, "passed": s.passed,
                 "message": s.message, "shortfall": s.shortfall,
                 "thieu_du_lieu": s.thieu_du_lieu}
                for s in r.screens.get(sym, [])
            ],
        })

    return {
        "as_of": as_of.isoformat(),
        "ky_review": ky_review,
        "constituents": r.constituents,
        "reserve": r.reserve,
        "missing_data": sorted(set(r.missing_data)),
        "stocks": stocks,
        "lich": {
            k: (v.isoformat() if isinstance(v, date) else v)
            for k, v in ky_review_ke_tiep(as_of).items()
        },
        "lich_su": lich_su or {},
        "xap_xi": XAP_XI,
        # Canh bao chung o cap toan bo ro (vd chon duoc < 30 ma) - lay tu BasketResult.canh_bao
        "canh_bao": r.canh_bao,
        "nguon_quy_tac": "HOSE-Index Ground Rules v4.0 (QĐ 747/QĐ-SGDHCM, 30/12/2024)",
    }


def main() -> None:
    as_of = date.today()
    start = as_of - timedelta(days=load_thresholds()["lookback"]["months"] * 31)

    manual = load_manual(MANUAL_FILE)
    prev = json.loads(PREV_BASKET_FILE.read_text(encoding="utf-8")) if PREV_BASKET_FILE.exists() else []
    free_float, ky_cbtt = load_free_float_moi_nhat(HOSE_INDEX_DIR)
    if ky_cbtt:
        logger.info("Free float lấy từ công bố chính thức HOSE kỳ %s (%d mã)", ky_cbtt, len(free_float))
    else:
        logger.warning("Chưa có file data/hose_index/*.yaml - chạy scripts/cap_nhat_cbtt.py trước. "
                       "Mọi mã sẽ thiếu free float.")

    symbols = fetch_hose_universe()
    logger.info("Vũ trụ HOSE: %d mã", len(symbols))

    # --- Sang thu von hoa HIEN TAI cho TOAN BO san bang 1 luot goi re (price_board) ---
    # roi chi lay lich su gia 12 thang (goi API ton kem, gioi han request/phut tren
    # GitHub Actions) cho N ma dung dau - xem giai thich o rules/thresholds.yaml,
    # vn30.so_ma_lay_lich_su_gia.
    von_hoa_hien_tai = fetch_current_market_cap(symbols)
    so_ma_lay_lich_su = load_thresholds()["vn30"]["so_ma_lay_lich_su_gia"]
    xep_hang_hien_tai = sorted(von_hoa_hien_tai, key=lambda s: -von_hoa_hien_tai[s])
    ma_lay_lich_su = xep_hang_hien_tai[:so_ma_lay_lich_su]
    logger.info(
        "Vốn hóa hiện tại tính được cho %d/%d mã; lấy lịch sử giá 12 tháng cho top %d mã",
        len(von_hoa_hien_tai), len(symbols), len(ma_lay_lich_su),
    )

    # --- Kiem chung gia dinh: khoang cach von hoa hien tai giua hang 40 va hang 100 ---
    # phai du lon, neu khong bien an toan 100 la qua hep (xem YEU CAU o task).
    top_n_dieu_kien = load_thresholds()["vn30"]["conditional_rank_max"]
    if len(xep_hang_hien_tai) >= so_ma_lay_lich_su:
        vh_hang_40 = von_hoa_hien_tai[xep_hang_hien_tai[top_n_dieu_kien - 1]]
        vh_hang_100 = von_hoa_hien_tai[xep_hang_hien_tai[so_ma_lay_lich_su - 1]]
        ty_le = vh_hang_100 / vh_hang_40 if vh_hang_40 else None
        logger.info(
            "Kiểm chứng biên an toàn: vốn hóa hạng %d = %.1f tỷ, hạng %d = %.1f tỷ (tỷ lệ %s)",
            top_n_dieu_kien, vh_hang_40 / 1e9, so_ma_lay_lich_su, vh_hang_100 / 1e9,
            f"{ty_le:.1%}" if ty_le is not None else "N/A",
        )
        if ty_le is not None and ty_le > 0.5:
            logger.warning(
                "CẢNH BÁO: vốn hóa hạng %d bằng %.1f%% vốn hóa hạng %d — biên an toàn "
                "top %d có thể QUÁ HẸP, cần xem lại vn30.so_ma_lay_lich_su_gia.",
                so_ma_lay_lich_su, ty_le * 100, top_n_dieu_kien, so_ma_lay_lich_su,
            )

    shares = fetch_shares_outstanding(ma_lay_lich_su)
    # Lay gia ca san bang 1 lan goi batch (khong lap tung ma) de phat hien duoc
    # loi ha tang (mat mang/API sap) thay vi am tham hieu nham la ca san khong giao dich.
    # Chi lay cho top N ma theo von hoa hien tai (xem giai thich o tren).
    daily_map = fetch_daily_batch(ma_lay_lich_su, start, as_of)
    symbols = ma_lay_lich_su

    # --- Vong 1: chua co LNST, chi de xep hang GTVH tren TOAN BO vu tru ---
    # (GTVH khong phu thuoc LNST, nen ket qua xep hang o vong nay da dung; vong 2
    # chi bo sung LNST cho top N ma de sang loc Dieu 4.3.1.d, khong doi xep hang.)
    ds_so_bo = lap_stock_inputs(symbols, daily_map, shares, manual, prev, free_float, start=start)
    kq_so_bo = build_vn30(ds_so_bo, as_of)
    top_n = load_thresholds()["vn30"]["consideration_list_size"]
    ma_can_lnst = sorted(
        kq_so_bo.metrics, key=lambda s: kq_so_bo.metrics[s]["gtvh_rank"]
    )[:top_n]
    logger.info("Gọi BCTC lấy LNST cho %d mã (top %d theo GTVH)", len(ma_can_lnst), top_n)

    lnst_auto = fetch_lnst_batch(ma_can_lnst)
    logger.info("Lấy được LNST tự động cho %d/%d mã", len(lnst_auto), len(ma_can_lnst))

    # --- Vong 2: chay lai voi LNST da co, ra ket qua chinh thuc ---
    ds = lap_stock_inputs(symbols, daily_map, shares, manual, prev, free_float, lnst_auto, start=start)
    logger.info("Chạy bộ quy tắc trên %d mã", len(ds))
    kq = build_vn30(ds, as_of)
    kq.canh_bao.extend(canh_bao_ma_ro_cu_bien_mat(prev, ds))

    # Ghi snapshot tho (chua co khoi lich/lich_su) truoc, roi moi gom lich su - de
    # chuoi sparkline co ca diem cua hom nay, khong bi cham 1 nhip.
    ky = ky_review_ke_tiep(as_of)["ky"]
    snapshot_tho = xuat_json(kq, as_of, ky)

    DATA_DIR.mkdir(exist_ok=True)
    hist = DATA_DIR / "history"
    hist.mkdir(exist_ok=True)
    (hist / f"{as_of.isoformat()}.json").write_text(
        json.dumps(snapshot_tho, ensure_ascii=False, indent=2), encoding="utf-8")

    lich_su = gom_lich_su(hist)
    out = xuat_json(kq, as_of, ky, lich_su)
    (DATA_DIR / "latest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # Site doc ./data/latest.json tuong doi voi chinh no -> giu mot ban trong site/
    import shutil
    site_data = ROOT / "site" / "data"
    site_data.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DATA_DIR / "latest.json", site_data / "latest.json")

    logger.info("Rổ dự kiến: %s", ", ".join(kq.constituents))
    if kq.missing_data:
        logger.warning("THIẾU DỮ LIỆU cho %d mã: %s",
                       len(set(kq.missing_data)), ", ".join(sorted(set(kq.missing_data))[:20]))
    if kq.canh_bao:
        for cb in kq.canh_bao:
            logger.warning("CẢNH BÁO: %s", cb)


if __name__ == "__main__":
    main()
