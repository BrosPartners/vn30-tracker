"""Ghep 7 buoc sang loc thanh mot lan chay hoan chinh (Dieu 4.3.1)."""
from datetime import date

from rules.definitions import (
    gtgd_kl, gtvh, gtvh_f, klgd_kl, listing_months, round_free_float, turnover_ratio, ty,
)
from rules.models import BasketResult, ScreenResult, StockInput
from rules.screens import (
    screen_eligibility,
    screen_free_float,
    screen_liquidity,
    screen_profit,
    screen_vn30_liquidity,
)
from rules.thresholds import load_thresholds


def build_vn30(stocks: list[StockInput], as_of: date) -> BasketResult:
    t = load_thresholds()["vn30"]
    result = BasketResult()

    # --- Tinh so lieu tren TOAN BO vu tru ---
    for s in stocks:
        result.metrics[s.symbol] = {
            "gtvh": gtvh(s),
            "gtvh_f": gtvh_f(s),
            "gtgd_kl": gtgd_kl(s),
            "klgd_kl": klgd_kl(s),
            "turnover": turnover_ratio(s),
            "free_float": s.free_float,
            "free_float_rounded": None if s.free_float is None else round_free_float(s.free_float),
            "in_previous_basket": s.in_previous_basket,
            "audit_opinion": s.audit_opinion,
            "lnst_ty": s.lnst_ty,
            "lnst_ky": s.lnst_ky,
            "lnst_nguon": s.lnst_nguon,
            "niem_yet_nguon": s.niem_yet_nguon,
            # So thang chi tinh duoc khi co listing_date cu the; ma "truoc cua so"
            # chi biet la du 6 thang, khong biet chinh xac bao nhieu thang -> None.
            "niem_yet_thang": None if s.listing_date is None else listing_months(s, as_of),
        }
        # Thieu ca listing_date CU THE lan bang chung "truoc cua so" moi la thieu du lieu -
        # niem_yet_truoc_cua_so=True la bang chung hop le, khong duoc coi la thieu.
        thieu_niem_yet = s.listing_date is None and not s.niem_yet_truoc_cua_so
        if s.free_float is None or s.lnst_positive is None or thieu_niem_yet:
            result.missing_data.append(s.symbol)

    # Xep hang GTVH giam dan; dong hang uu tien GTGD_KL lon hon (Dieu 4.3.1.e)
    def _khoa_gtvh(s: StockInput) -> tuple:
        m = result.metrics[s.symbol]
        return (-m["gtvh"], -m["gtgd_kl"])

    xep = sorted(stocks, key=_khoa_gtvh)
    for hang, s in enumerate(xep, start=1):
        result.metrics[s.symbol]["gtvh_rank"] = hang

    # --- 3 buoc sang loc VNAllshare: eligibility, free_float, liquidity ---
    vnallshare = []
    # Ma bi loai o vong nay MA MOI ly do truot deu la thieu du lieu (khong co ly
    # do truot thuc chat nao) VA hang von hoa cua no van nam trong vung duoc chon
    # (<= conditional_rank_max) - nghia la neu co du du lieu, rat co the no da
    # duoc xet vao ro. Phai canh bao ro cho nguoi doc, KHONG duoc de am tham.
    ma_thieu_du_lieu_hang_cao = []
    for s in xep:
        m = result.metrics[s.symbol]
        buoc = [
            screen_eligibility(s, as_of, m["gtvh_rank"]),
            screen_free_float(s, m["gtvh_f"]),
            screen_liquidity(s, m["turnover"]),
        ]
        result.screens[s.symbol] = buoc
        if all(b.passed for b in buoc):
            vnallshare.append(s)
        else:
            that_bai = [b for b in buoc if not b.passed]
            if that_bai and all(b.thieu_du_lieu for b in that_bai) \
                    and m["gtvh_rank"] <= t["conditional_rank_max"]:
                ma_thieu_du_lieu_hang_cao.append(s.symbol)

    # --- Dieu 4.3.1.a: loai ma KLGD_KL < nguong; Dieu 4.3.1.b: loai ma GTGD_KL < nguong ---
    sau_a = []          # da qua buoc a (con lai sau khi loai theo KLGD_KL)
    for s in vnallshare:
        m = result.metrics[s.symbol]
        ket_qua_ab = screen_vn30_liquidity(s, m["klgd_kl"], m["gtgd_kl"])
        result.screens[s.symbol].append(ket_qua_ab)
        if not ket_qua_ab.passed and ket_qua_ab.rule_ref.endswith(".a"):
            continue  # loai han o buoc a, khong duoc xem xet o buoc b
        sau_a.append(s)

    xem_xet = [s for s in sau_a if result.screens[s.symbol][-1].passed]
    duoi_nguong_gtgd = [s for s in sau_a if not result.screens[s.symbol][-1].passed]

    # Neu danh sach xem xet chua du 50 ma, bu them tu nhom duoi nguong GTGD_KL,
    # xep giam dan theo GTGD_KL, dong hang uu tien GTVH lon hon (Dieu 4.3.1.b).
    so_luong_can = t["consideration_list_size"]
    if len(xem_xet) < so_luong_can:
        con_thieu = so_luong_can - len(xem_xet)
        ung_vien_bu = sorted(
            duoi_nguong_gtgd,
            key=lambda s: (-result.metrics[s.symbol]["gtgd_kl"], -result.metrics[s.symbol]["gtvh"]),
        )
        for s in ung_vien_bu[:con_thieu]:
            m = result.metrics[s.symbol]
            ket_qua_bu = ScreenResult(
                s.symbol, "vn30_liquidity", t["rule_ref"] + ".b", True,
                f"GTGD khớp lệnh {ty(m['gtgd_kl'])}/phiên dưới ngưỡng {ty(t['min_gtgd_kl_vnd'])}, "
                f"nhưng được lấy bù cho đủ {so_luong_can} mã trong danh sách xem xét",
            )
            result.screens[s.symbol][-1] = ket_qua_bu
            xem_xet.append(s)

    # --- Dieu 4.3.1.c-d: sang loc loi nhuan (canh bao/kiem soat da xu ly o eligibility) ---
    dat = []
    for s in xem_xet:
        ket_qua_profit = screen_profit(s)
        result.screens[s.symbol].append(ket_qua_profit)
        if ket_qua_profit.passed:
            dat.append(s)

    # --- Dieu 4.3.1.e: sap xep lai theo GTVH giam dan, dong hang uu tien GTGD_KL ---
    dat = sorted(dat, key=_khoa_gtvh)

    # --- Dieu 4.3.1.f: top 20 vao thang; 21-40 uu tien ma ro cu ---
    trong_vung = dat[: t["conditional_rank_max"]]
    chon = [s.symbol for s in trong_vung[: t["auto_include_rank"]]]
    con_lai = trong_vung[t["auto_include_rank"]:]

    for s in con_lai:                      # uu tien ma da co trong ro ky truoc
        if len(chon) >= t["basket_size"]:
            break
        if s.in_previous_basket:
            chon.append(s.symbol)
    for s in con_lai:                      # roi den ma moi
        if len(chon) >= t["basket_size"]:
            break
        if s.symbol not in chon:
            chon.append(s.symbol)

    result.constituents = chon

    # --- Dieu 4.3.1.g: 5 ma GTVH lon nhat con lai ---
    result.reserve = [s.symbol for s in dat if s.symbol not in chon][: t["reserve_size"]]

    # --- Canh bao neu co ma du hang von hoa vao ro nhung bi loai vi thieu du lieu ---
    if ma_thieu_du_lieu_hang_cao:
        ds_ma = ", ".join(sorted(ma_thieu_du_lieu_hang_cao))
        result.canh_bao.append(
            f"Mã {ds_ma} có hạng vốn hóa đủ điều kiện vào rổ (hạng ≤ "
            f"{t['conditional_rank_max']}) nhưng bị loại khỏi vòng xét ở bước sàng lọc "
            "VNAllshare CHỈ VÌ THIẾU DỮ LIỆU đầu vào (free float/ngày niêm yết/LNST chưa "
            "có), không phải vì không đạt tiêu chí thực chất. Vì vậy rổ dự kiến hiện tại "
            "KHÔNG đáng tin cậy đầy đủ — các mã đang lấp vào chỗ trống của những mã này "
            "không nên được đọc như một dự báo chắc chắn, mà cần chờ bổ sung dữ liệu."
        )

    # --- Canh bao neu ro khong du 30 ma: dau hieu du lieu dau vao chua du ---
    if len(result.constituents) < t["basket_size"]:
        result.canh_bao.append(
            f"Chỉ chọn được {len(result.constituents)}/{t['basket_size']} mã cho rổ VN30 — "
            "dữ liệu đầu vào (giá, khối lượng, free float, LNST...) có thể chưa đủ để xét đủ số mã theo quy tắc."
        )

    return result
