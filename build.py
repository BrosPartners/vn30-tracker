"""Dieu phoi: collector -> bo quy tac -> data/latest.json + snapshot lich su.

Chay tay:  python build.py
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from collectors.manual_data import load_manual
from collectors.market_data import fetch_daily_batch, fetch_hose_universe, fetch_shares_outstanding
from rules.basket import build_vn30
from rules.models import BasketResult, StockInput
from rules.thresholds import load_thresholds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MANUAL_FILE = DATA_DIR / "manual.yaml"
PREV_BASKET_FILE = DATA_DIR / "previous_basket.json"

XAP_XI = [
    "GTGD chưa gồm giao dịch thỏa thuận (nguồn dữ liệu chỉ có khớp lệnh) — "
    "turnover ratio là ước tính cận dưới.",
    "GTVH 12 tháng dùng số cổ phiếu lưu hành hiện tại cho toàn chuỗi giá quá khứ — "
    "lệch với mã có phát hành thêm hoặc chia thưởng trong kỳ.",
    "Ý kiến kiểm toán không đọc được tự động — mã chưa xác nhận hiển thị là "
    "'chưa xác nhận', không mặc định là đạt.",
]


def lap_stock_inputs(symbols, daily_map, shares_map, manual, previous_basket) -> list[StockInput]:
    """Ghep so tu may (daily, SLCP) voi so nguoi xac nhan (manual) thanh StockInput.

    Bo qua ma khong co SLCP hoac khong co du lieu gia (daily rong/thieu) - rules/definitions.py
    se nem ValueError neu dua daily rong vao, nen phai loc truoc o day.
    """
    prev = {s.upper() for s in previous_basket}
    ds: list[StockInput] = []
    for sym in symbols:
        sym = sym.upper()
        slcp = shares_map.get(sym)
        daily = daily_map.get(sym)
        if not slcp or daily is None or daily.empty:
            continue
        m = manual.get(sym, {})
        ds.append(StockInput(
            symbol=sym,
            daily=daily,
            shares_outstanding=slcp,
            listing_date=m.get("listing_date", date(1900, 1, 1)),
            free_float=m.get("free_float"),
            in_previous_basket=sym in prev,
            warning_status=m.get("warning_status", "none"),
            lnst_positive=m.get("lnst_positive"),
            audit_opinion=m.get("audit_opinion", "unknown"),
        ))
    return ds


def _ket_luan(symbol: str, r: BasketResult) -> str:
    if symbol in r.constituents:
        return "Trong rổ dự kiến"
    if symbol in r.reserve:
        return "Dự phòng"
    if symbol in r.missing_data:
        return "Thiếu dữ liệu"
    return "Không đạt"


def xuat_json(r: BasketResult, as_of: date, ky_review: str) -> dict:
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
            "ket_luan": _ket_luan(sym, r),
            # Nhan canh bao rieng cho tung ma - khong duoc am tham bo (spec muc 4.3)
            "canh_bao": ([] if m["audit_opinion"] == "unqualified"
                         else ["Chưa xác nhận ý kiến kiểm toán"]),
            "screens": [
                {"step": s.step, "rule_ref": s.rule_ref, "passed": s.passed,
                 "message": s.message, "shortfall": s.shortfall}
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

    symbols = fetch_hose_universe()
    logger.info("Vũ trụ HOSE: %d mã", len(symbols))

    shares = fetch_shares_outstanding(symbols)
    # Lay gia ca san bang 1 lan goi batch (khong lap tung ma) de phat hien duoc
    # loi ha tang (mat mang/API sap) thay vi am tham hieu nham la ca san khong giao dich.
    daily_map = fetch_daily_batch(symbols, start, as_of)

    ds = lap_stock_inputs(symbols, daily_map, shares, manual, prev)
    logger.info("Chạy bộ quy tắc trên %d mã", len(ds))
    kq = build_vn30(ds, as_of)

    ky = "07/2026"
    out = xuat_json(kq, as_of, ky)

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "latest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    hist = DATA_DIR / "history"
    hist.mkdir(exist_ok=True)
    (hist / f"{as_of.isoformat()}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Rổ dự kiến: %s", ", ".join(kq.constituents))
    if kq.missing_data:
        logger.warning("THIẾU DỮ LIỆU cho %d mã: %s",
                       len(set(kq.missing_data)), ", ".join(sorted(set(kq.missing_data))[:20]))
    if kq.canh_bao:
        for cb in kq.canh_bao:
            logger.warning("CẢNH BÁO: %s", cb)


if __name__ == "__main__":
    main()
