from datetime import date

import pandas as pd
import pytest

from rules.definitions import (
    PRICE_UNIT_VND,
    average_of_monthly_medians,
    gtvh,
    gtvh_f,
    gtgd_kl,
    klgd_kl,
    listing_months,
    round_free_float,
    turnover_ratio,
)
from rules.models import StockInput


def _stock(close, volume, times, shares=1_000_000, free_float=None, listing=date(2020, 1, 1)):
    return StockInput(
        symbol="TEST",
        daily=pd.DataFrame({"time": pd.to_datetime(times), "close": close, "volume": volume}),
        shares_outstanding=shares,
        listing_date=listing,
        free_float=free_float,
    )


def test_binh_quan_cua_trung_vi_khac_binh_quan_thuong():
    """Thang 1 co 3 phien (trung vi 2), thang 2 co 1 phien (trung vi 100).
    Binh quan cua trung vi = (2 + 100)/2 = 51, KHONG phai binh quan thuong 26,5."""
    times = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-02-02"]
    s = pd.Series([1.0, 2.0, 3.0, 100.0])
    assert average_of_monthly_medians(s, pd.to_datetime(pd.Series(times))) == pytest.approx(51.0)


def test_gia_tinh_bang_nghin_dong():
    """vnstock tra gia theo nghin dong -> von hoa phai nhan 1000."""
    assert PRICE_UNIT_VND == 1000
    st = _stock([10.0], [0], ["2026-01-05"], shares=1_000_000)
    # 10 nghin dong x 1.000.000 cp = 10 ty dong
    assert gtvh(st) == pytest.approx(10e9)


def test_gtvh_la_binh_quan_von_hoa_hang_ngay_khong_phai_von_hoa_hom_nay():
    st = _stock([10.0, 20.0], [0, 0], ["2026-01-05", "2026-01-06"], shares=1_000_000)
    assert gtvh(st) == pytest.approx(15e9)


def test_gtgd_kl_va_klgd_kl():
    times = ["2026-01-05", "2026-01-06", "2026-02-02"]
    st = _stock([10.0, 10.0, 20.0], [100, 300, 500], times)
    # Thang 1: gia tri ngay = 1.000.000 va 3.000.000 -> trung vi 2.000.000
    # Thang 2: 10.000.000 -> trung vi 10.000.000 ; binh quan = 6.000.000
    assert gtgd_kl(st) == pytest.approx(6_000_000)
    # KL: thang 1 trung vi 200, thang 2 la 500 -> binh quan 350
    assert klgd_kl(st) == pytest.approx(350.0)


def test_thieu_free_float_tra_none_chu_khong_doan():
    st = _stock([10.0], [100], ["2026-01-05"], free_float=None)
    assert gtvh_f(st) is None
    assert turnover_ratio(st) is None


def test_turnover_ratio():
    st = _stock([10.0, 10.0], [100, 100], ["2026-01-05", "2026-02-05"],
                shares=1_000_000, free_float=0.5)
    # GTVH = 10e9 ; GTVH_f = 5e9 ; GTGD_KL = 1.000.000
    assert turnover_ratio(st) == pytest.approx(1_000_000 / 5e9)


@pytest.mark.parametrize("raw,rounded", [
    (0.004, 0.01),    # <= 15% lam tron len boi so 1%
    (0.10, 0.10),
    (0.121, 0.13),
    (0.15, 0.15),
    (0.151, 0.20),    # > 15% lam tron len boi so 5%
    (0.32, 0.35),
    (0.95, 0.95),
    (0.96, 1.00),
])
def test_lam_tron_free_float(raw, rounded):
    assert round_free_float(raw) == pytest.approx(rounded)


def test_so_thang_niem_yet():
    st = _stock([10.0], [0], ["2026-01-05"], listing=date(2025, 7, 15))
    assert listing_months(st, date(2026, 7, 15)) == 12
    assert listing_months(st, date(2026, 1, 14)) == 5
