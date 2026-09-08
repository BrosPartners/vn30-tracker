from datetime import date

import pandas as pd

from rules.models import StockInput
from rules.screens import screen_eligibility, screen_free_float, screen_liquidity


def _stock(**kw):
    base = dict(
        symbol="TEST",
        daily=pd.DataFrame({"time": pd.to_datetime(["2026-01-05"]), "close": [10.0], "volume": [100]}),
        shares_outstanding=1_000_000,
        listing_date=date(2020, 1, 1),
    )
    base.update(kw)
    return StockInput(**base)


AS_OF = date(2026, 7, 1)


def test_niem_yet_du_6_thang_thi_dat():
    r = screen_eligibility(_stock(listing_date=date(2026, 1, 1)), AS_OF, gtvh_rank=100)
    assert r.passed and r.rule_ref == "3.2"


def test_niem_yet_duoi_6_thang_thi_truot():
    r = screen_eligibility(_stock(listing_date=date(2026, 4, 1)), AS_OF, gtvh_rank=100)
    assert not r.passed
    assert "6 tháng" in r.message
    assert r.shortfall == 3      # con thieu 3 thang


def test_ma_top5_von_hoa_niem_yet_tren_3_thang_duoc_mien():
    r = screen_eligibility(_stock(listing_date=date(2026, 3, 1)), AS_OF, gtvh_rank=4)
    assert r.passed
    assert "top 5" in r.message


def test_ma_top5_nhung_moi_niem_yet_2_thang_van_truot():
    r = screen_eligibility(_stock(listing_date=date(2026, 5, 1)), AS_OF, gtvh_rank=4)
    assert not r.passed


def test_ma_bi_kiem_soat_thi_truot():
    r = screen_eligibility(_stock(warning_status="control"), AS_OF, gtvh_rank=10)
    assert not r.passed
    assert "kiểm soát" in r.message


def test_free_float_tu_10_phan_tram_tro_len_thi_dat():
    r = screen_free_float(_stock(free_float=0.10), gtvh_f_value=1e9)
    assert r.passed


def test_free_float_duoi_10_duoc_cuu_neu_von_hoa_free_float_du_lon():
    """Ma MOI: nguong cuu la 2.500 ty."""
    r = screen_free_float(_stock(free_float=0.04, in_previous_basket=False), gtvh_f_value=2.6e12)
    assert r.passed
    assert "ngoại lệ" in r.message


def test_ma_moi_free_float_thap_von_hoa_khong_du_thi_truot():
    r = screen_free_float(_stock(free_float=0.04, in_previous_basket=False), gtvh_f_value=2.1e12)
    assert not r.passed
    assert r.shortfall == 0.4e12      # thieu 400 ty so voi nguong 2.500 ty


def test_ma_trong_ro_ky_truoc_duoc_nguong_cuu_thap_hon():
    """Cung 2.100 ty: ma cu DAT (nguong 2.000), ma moi TRUOT (nguong 2.500)."""
    r = screen_free_float(_stock(free_float=0.04, in_previous_basket=True), gtvh_f_value=2.1e12)
    assert r.passed


def test_thieu_free_float_thi_truot_va_noi_ro_la_thieu_du_lieu():
    r = screen_free_float(_stock(free_float=None), gtvh_f_value=None)
    assert not r.passed
    assert "thiếu dữ liệu" in r.message.lower()


def test_turnover_ma_moi_can_005_phan_tram():
    assert screen_liquidity(_stock(in_previous_basket=False), 0.0005).passed
    assert not screen_liquidity(_stock(in_previous_basket=False), 0.00049).passed


def test_turnover_ma_trong_ro_chi_can_004_phan_tram():
    """Cung 0,045%: ma trong ro DAT, ma ngoai ro TRUOT."""
    assert screen_liquidity(_stock(in_previous_basket=True), 0.00045).passed
    assert not screen_liquidity(_stock(in_previous_basket=False), 0.00045).passed


def test_turnover_khong_tinh_duoc_vi_thieu_free_float():
    """Khi free_float is None -> khong the tinh turnover, thieu du lieu."""
    r = screen_liquidity(_stock(free_float=None), None)
    assert not r.passed
    assert "thiếu dữ liệu free float" in r.message
    assert "cần cập nhật thủ công" in r.message


def test_turnover_khong_tinh_duoc_vi_free_float_bang_0():
    """Khi free_float == 0% -> turnover khong xac dinh vi chia cho 0."""
    r = screen_liquidity(_stock(free_float=0.0), None)
    assert not r.passed
    assert "free float bằng 0%" in r.message


def test_free_float_trang_thai_dung_nhung_gtvh_f_value_none_la_loi():
    """Khi free_float khong None nhung gtvh_f_value la None -> loi lap trinh."""
    r = screen_free_float(_stock(free_float=0.05), gtvh_f_value=None)
    assert not r.passed
    assert "không có giá trị vốn hóa free-float" in r.message
