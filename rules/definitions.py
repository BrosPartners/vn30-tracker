"""Dinh nghia so lieu theo Dieu 3.1 va 3.3.5, Ground Rules v4.0.

Quy uoc don vi trong toan he thong:
  - Tien: VND (khong phai nghin, khong phai ty). Chi doi sang ty o tang hien thi.
  - vnstock tra 'close' theo NGHIN DONG -> nhan PRICE_UNIT_VND.
"""
import math
from datetime import date
from typing import Optional

import pandas as pd

from rules.models import StockInput

PRICE_UNIT_VND = 1000


def average_of_monthly_medians(values: pd.Series, times: pd.Series) -> float:
    """Dieu 3.1: trung vi theo TUNG THANG duong lich, roi binh quan cac trung vi do.

    Khong phai binh quan thuong: thang it phien van co trong so ngang thang nhieu phien.
    """
    if len(values) == 0:
        return 0.0
    df = pd.DataFrame({"v": values.to_numpy(), "t": pd.to_datetime(times).to_numpy()})
    monthly = df.groupby(df["t"].dt.to_period("M"))["v"].median()
    return float(monthly.mean())


def _daily_market_cap(stock: StockInput) -> pd.Series:
    return stock.daily["close"] * PRICE_UNIT_VND * stock.shares_outstanding


def gtvh(stock: StockInput) -> float:
    """Binh quan von hoa HANG NGAY trong ky nhin lai (Dieu 3.1)."""
    if stock.daily.empty:
        return 0.0
    return float(_daily_market_cap(stock).mean())


def gtvh_f(stock: StockInput) -> Optional[float]:
    """Von hoa free-float. None neu thieu free float - khong duoc doan."""
    if stock.free_float is None:
        return None
    return gtvh(stock) * stock.free_float


def gtgd_kl(stock: StockInput) -> float:
    """Gia tri giao dich khop lenh: binh quan cua trung vi thang (Dieu 3.1)."""
    if stock.daily.empty:
        return 0.0
    daily_value = stock.daily["close"] * PRICE_UNIT_VND * stock.daily["volume"]
    return average_of_monthly_medians(daily_value, stock.daily["time"])


def klgd_kl(stock: StockInput) -> float:
    """Khoi luong giao dich khop lenh: binh quan cua trung vi thang (Dieu 3.1)."""
    if stock.daily.empty:
        return 0.0
    return average_of_monthly_medians(stock.daily["volume"], stock.daily["time"])


def turnover_ratio(stock: StockInput) -> Optional[float]:
    """Dieu 3.4: GTGD / GTVH_f.

    XAP XI DA BIET: quy tac goc dung GTGD gom ca khop lenh VA thoa thuan; o day
    chi co khop lenh -> ket qua la CAN DUOI. Xem spec muc 4.3.
    """
    denom = gtvh_f(stock)
    if denom is None or denom == 0:
        return None
    return gtgd_kl(stock) / denom


def round_free_float(f: float) -> float:
    """Dieu 3.3.5: f <= 15% lam tron LEN boi so 1%; f > 15% lam tron LEN boi so 5%."""
    step = 0.01 if f <= 0.15 else 0.05
    return round(math.ceil(round(f / step, 9)) * step, 4)


def listing_months(stock: StockInput, as_of: date) -> int:
    """So thang tron da niem yet tinh toi ngay chot du lieu."""
    d = stock.listing_date
    months = (as_of.year - d.year) * 12 + (as_of.month - d.month)
    if as_of.day < d.day:
        months -= 1
    return months
