"""Ba bước sàng lọc của Ground Rules v4.0.

Mỗi hàm trả về một ScreenResult mang câu giải thích tiếng Việt - chuỗi này hiện
thẳng lên web ("vượt tiêu chí nào"), nên phải viết cho người đọc chứ không phải cho log.
"""
from datetime import date
from typing import Optional

from rules.definitions import listing_months
from rules.models import ScreenResult, StockInput
from rules.thresholds import load_thresholds

_TRANG_THAI_XAU = {
    "warning": "cảnh báo",
    "control": "kiểm soát",
    "restricted": "hạn chế giao dịch",
    "suspended": "tạm ngừng giao dịch",
}


def _ty(x: float) -> str:
    """Định dạng số tiền thành tỷ đồng với dấu phân tách."""
    return f"{x / 1e9:,.0f} tỷ".replace(",", ".")


def screen_eligibility(stock: StockInput, as_of: date, gtvh_rank: int) -> ScreenResult:
    """Điều 3.2: trạng thái giao dịch và thời gian niêm yết."""
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

    if gtvh_f_value is not None and gtvh_f_value >= nguong:
        return ScreenResult(
            stock.symbol, "free_float", ref, True,
            f"Free float {stock.free_float:.0%} dưới 10% nhưng đạt ngoại lệ: "
            f"vốn hóa free-float {_ty(gtvh_f_value)} ≥ {_ty(nguong)} (mã {loai})",
        )

    # Không đạt điều kiện và không đủ ngoại lệ
    thuc = gtvh_f_value or 0.0
    return ScreenResult(
        stock.symbol, "free_float", ref, False,
        f"Free float {stock.free_float:.0%} dưới 10% và vốn hóa free-float "
        f"{_ty(thuc)} chưa đạt ngoại lệ {_ty(nguong)} (mã {loai})",
        shortfall=nguong - thuc,
    )


def screen_liquidity(stock: StockInput, turnover: Optional[float]) -> ScreenResult:
    """Điều 3.4: Tỷ lệ thanh khoản (Turnover Ratio) = GTGD / GTVH_f."""
    t = load_thresholds()["liquidity"]
    ref = t["rule_ref"]

    if turnover is None:
        return ScreenResult(stock.symbol, "liquidity", ref, False,
                            "Không tính được turnover do thiếu free float")

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
