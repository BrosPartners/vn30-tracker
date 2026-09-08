"""Ba bước sàng lọc của Ground Rules v4.0.

Mỗi hàm trả về một ScreenResult mang câu giải thích tiếng Việt - chuỗi này hiện
thẳng lên web ("vượt tiêu chí nào"), nên phải viết cho người đọc chứ không phải cho log.
"""
from datetime import date
from typing import Optional

from rules.definitions import gtvh_f, listing_months, ty
from rules.models import ScreenResult, StockInput
from rules.thresholds import load_thresholds

_TRANG_THAI_XAU = {
    "warning": "cảnh báo",
    "control": "kiểm soát",
    "restricted": "hạn chế giao dịch",
    "suspended": "tạm ngừng giao dịch",
}


def screen_eligibility(stock: StockInput, as_of: date, gtvh_rank: int) -> ScreenResult:
    """Điều 3.2: trạng thái giao dịch và thời gian niêm yết.

    Lưu ý về giới hạn: Điều 3.2 quy định cảnh báo/kiểm soát trong vòng 3 tháng gần nhất,
    nhưng kiểm tra này chỉ xem TRẠNG THÁI HIỆN TẠI từ dữ liệu đầu vào (StockInput không
    có trường ngày bắt đầu cảnh báo). Người nhập warning_status trong data/manual.yaml
    chịu trách nhiệm phản ánh toàn bộ giai đoạn 3 tháng.
    """
    t = load_thresholds()["eligibility"]
    ref = t["rule_ref"]

    # Kiểm tra cảnh báo/kiểm soát
    if stock.warning_status in _TRANG_THAI_XAU:
        return ScreenResult(
            stock.symbol, "eligibility", ref, False,
            f"Đang bị {_TRANG_THAI_XAU[stock.warning_status]} trong "
            f"{t['warning_lookback_months']} tháng gần nhất",
        )

    months = listing_months(stock, as_of)

    # Kiểm tra điều kiện cơ bản: 6 tháng
    if months >= t["min_listing_months"]:
        return ScreenResult(stock.symbol, "eligibility", ref, True,
                            f"Đã niêm yết {months} tháng")

    # Ngoại lệ: top 5 GTVH chỉ cần 3 tháng
    mien = (gtvh_rank <= t["top_gtvh_exemption_rank"]
            and months > t["top_gtvh_exemption_months"])
    if mien:
        return ScreenResult(
            stock.symbol, "eligibility", ref, True,
            f"Niêm yết {months} tháng nhưng được miễn theo ngoại lệ top 5 vốn hóa",
        )

    return ScreenResult(
        stock.symbol, "eligibility", ref, False,
        f"Mới niêm yết {months} tháng, chưa đủ {t['min_listing_months']} tháng",
        shortfall=t["min_listing_months"] - months,
    )


def screen_free_float(stock: StockInput, gtvh_f_value: Optional[float]) -> ScreenResult:
    """Điều 3.3.3: f >= 10%, hoặc ngoại lệ cho mã free float thấp nhưng vốn hóa free-float lớn.

    Lưu ý: ngưỡng 2.000/2.500 tỷ CHỈ áp cho mã f < 10%, không phải điều kiện chung.
    """
    t = load_thresholds()["free_float"]
    ref = t["rule_ref"]

    # Thiếu dữ liệu free float
    if stock.free_float is None:
        return ScreenResult(stock.symbol, "free_float", ref, False,
                            "Thiếu dữ liệu free float — cần cập nhật thủ công")

    # Đạt điều kiện cơ bản: >= 10%
    if stock.free_float >= t["min_ratio"]:
        return ScreenResult(stock.symbol, "free_float", ref, True,
                            f"Free float {stock.free_float:.0%}")

    # Free float < 10%: kiểm tra ngoại lệ GTVH free-float
    nguong = (t["exception_gtvh_f_existing_vnd"] if stock.in_previous_basket
              else t["exception_gtvh_f_new_vnd"])
    loai = "đang trong rổ" if stock.in_previous_basket else "ngoài rổ"

    # Kiểm tra dữ liệu gtvh_f_value một cách tường minh
    if gtvh_f_value is None:
        # Nếu free_float không None nhưng gtvh_f_value None -> lỗi lập trình (dữ liệu không nhất quán)
        return ScreenResult(
            stock.symbol, "free_float", ref, False,
            f"Lỗi dữ liệu: không có giá trị vốn hóa free-float để đối chiếu ngoại lệ (free float {stock.free_float:.0%})",
        )

    if gtvh_f_value >= nguong:
        return ScreenResult(
            stock.symbol, "free_float", ref, True,
            f"Free float {stock.free_float:.0%} dưới 10% nhưng đạt ngoại lệ: "
            f"vốn hóa free-float {ty(gtvh_f_value)} ≥ {ty(nguong)} (mã {loai})",
        )

    # Không đạt điều kiện và không đủ ngoại lệ
    return ScreenResult(
        stock.symbol, "free_float", ref, False,
        f"Free float {stock.free_float:.0%} dưới 10% và vốn hóa free-float "
        f"{ty(gtvh_f_value)} chưa đạt ngoại lệ {ty(nguong)} (mã {loai})",
        shortfall=nguong - gtvh_f_value,
    )


def screen_liquidity(stock: StockInput, turnover: Optional[float]) -> ScreenResult:
    """Điều 3.4: Tỷ lệ thanh khoản (Turnover Ratio) = GTGD / GTVH_f."""
    t = load_thresholds()["liquidity"]
    ref = t["rule_ref"]

    if turnover is None:
        # Phân biệt hai trường hợp khác nhau khi turnover không tính được
        gtvh_f_val = gtvh_f(stock)

        if gtvh_f_val is None:
            # Thiếu dữ liệu free float - không thể tính gtvh_f
            return ScreenResult(stock.symbol, "liquidity", ref, False,
                                "Không tính được turnover do thiếu dữ liệu free float — cần cập nhật thủ công")
        elif gtvh_f_val == 0:
            # Free float = 0% - không xác định được (chia cho 0)
            return ScreenResult(stock.symbol, "liquidity", ref, False,
                                "Không tính được turnover vì free float bằng 0%")

    # Ngưỡng khác nhau giữa mã mới và mã cũ
    nguong = (t["min_turnover_existing"] if stock.in_previous_basket
              else t["min_turnover_new"])

    if turnover >= nguong:
        return ScreenResult(stock.symbol, "liquidity", ref, True,
                            f"Turnover {turnover:.3%}")

    return ScreenResult(
        stock.symbol, "liquidity", ref, False,
        f"Turnover {turnover:.3%} dưới ngưỡng {nguong:.2%}",
        shortfall=nguong - turnover,
    )


def screen_vn30_liquidity(stock: StockInput, klgd_kl_value: float,
                          gtgd_kl_value: float) -> ScreenResult:
    """Dieu 4.3.1.a-b: KLGD_KL >= 300.000 cp VA GTGD_KL >= 30 ty."""
    t = load_thresholds()["vn30"]
    ref = t["rule_ref"]

    if klgd_kl_value < t["min_klgd_kl_shares"]:
        return ScreenResult(
            stock.symbol, "vn30_liquidity", ref + ".a", False,
            f"KLGD khớp lệnh {klgd_kl_value:,.0f} cp/phiên, dưới ngưỡng "
            f"{t['min_klgd_kl_shares']:,.0f} cp".replace(",", "."),
            shortfall=t["min_klgd_kl_shares"] - klgd_kl_value,
        )

    if gtgd_kl_value < t["min_gtgd_kl_vnd"]:
        return ScreenResult(
            stock.symbol, "vn30_liquidity", ref + ".b", False,
            f"GTGD khớp lệnh {ty(gtgd_kl_value)}/phiên, thiếu "
            f"{ty(t['min_gtgd_kl_vnd'] - gtgd_kl_value)} so với ngưỡng "
            f"{ty(t['min_gtgd_kl_vnd'])}",
            shortfall=t["min_gtgd_kl_vnd"] - gtgd_kl_value,
        )

    return ScreenResult(stock.symbol, "vn30_liquidity", ref + ".a-b", True,
                        f"KLGD {klgd_kl_value:,.0f} cp và GTGD {ty(gtgd_kl_value)}/phiên"
                        .replace(",", "."))


def screen_profit(stock: StockInput) -> ScreenResult:
    """Dieu 4.3.1.d: loai ma co LNST am.

    Quyet dinh 2026-09-08 (spec muc 4.3): y kien kiem toan CHUA xac nhan
    (audit_opinion != 'unqualified') KHONG tu loai ma - cau "chi xet BCTC co y kien
    chap nhan toan phan" la quy dinh chon bao cao lay so, khong phai tieu chi loai
    doc lap. Ma nhu vay van dat nhung mang nhan canh bao hien ro tren web.
    """
    ref = load_thresholds()["vn30"]["rule_ref"] + ".d"

    if stock.lnst_positive is None:
        return ScreenResult(stock.symbol, "profit", ref, False,
                            "Thiếu dữ liệu lợi nhuận sau thuế — cần xác nhận thủ công")
    if not stock.lnst_positive:
        return ScreenResult(stock.symbol, "profit", ref, False,
                            "Lợi nhuận sau thuế âm ở kỳ báo cáo gần nhất")
    if stock.audit_opinion != "unqualified":
        return ScreenResult(stock.symbol, "profit", ref, True,
                            "Lợi nhuận sau thuế dương, nhưng chưa xác nhận ý kiến kiểm toán")
    return ScreenResult(stock.symbol, "profit", ref, True,
                        "Lợi nhuận sau thuế dương, kiểm toán chấp nhận toàn phần")
