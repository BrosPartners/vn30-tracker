from datetime import date

import pandas as pd

from rules.models import StockInput
from rules.screens import screen_eligibility, screen_free_float, screen_liquidity, screen_profit


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


def test_thieu_ngay_niem_yet_thi_truot_khong_duoc_bia_ngay():
    """listing_date=None nghia la chua xac nhan - KHONG duoc doan la niem yet tu 1900."""
    r = screen_eligibility(_stock(listing_date=None), AS_OF, gtvh_rank=100)
    assert not r.passed
    assert "thiếu" in r.message.lower()
    assert "ngày niêm yết" in r.message.lower()


def test_niem_yet_truoc_cua_so_du_lieu_thi_dat_khong_bia_ngay():
    """Chuoi gia bat dau sat ngay dau cua so (suy ra da giao dich tu truoc do >= 12
    thang) - phai DAT nhung KHONG duoc bia ra mot listing_date cu the."""
    r = screen_eligibility(
        _stock(listing_date=None, niem_yet_truoc_cua_so=True), AS_OF, gtvh_rank=100)
    assert r.passed
    assert "trước cửa sổ dữ liệu" in r.message


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


def test_thieu_free_float_thi_danh_dau_thieu_du_lieu():
    """Truot vi THIEU free_float phai danh dau thieu_du_lieu=True de web
    khong xep vao nhom 'nguy co bi loai' (xem rules/models.ScreenResult)."""
    r = screen_free_float(_stock(free_float=None), gtvh_f_value=None)
    assert not r.passed
    assert r.thieu_du_lieu is True


def test_free_float_that_khong_dat_thi_khong_phai_thieu_du_lieu():
    """Truot vi ty le THAT khong dat nguong (co du lieu ro rang) - khong duoc
    danh dau thieu_du_lieu, day la truot THUC CHAT."""
    r = screen_free_float(_stock(free_float=0.04, in_previous_basket=False), gtvh_f_value=2.1e12)
    assert not r.passed
    assert r.thieu_du_lieu is False


def test_free_float_none_thong_thuong_thi_thieu_du_lieu():
    """Khong co bang chung HOSE da xet (hose_loai_khoi_vnallshare=False, mac dinh)
    -> phai la thieu du lieu nhu cu, khong duoc doi hanh vi mac dinh."""
    r = screen_free_float(_stock(free_float=None), gtvh_f_value=None)
    assert not r.passed
    assert r.thieu_du_lieu is True


def test_free_float_none_hose_da_loai_thi_khong_phai_thieu_du_lieu():
    """Ma khong co trong VNAllshare NHUNG co bang chung HOSE da xet va loai (vd
    da giao dich tu truoc ngay chot) -> KHONG duoc coi la thieu du lieu, message
    phai neu ro ky cong bo va Dieu 3.2-3.4."""
    r = screen_free_float(
        _stock(free_float=None, hose_loai_khoi_vnallshare=True, ky_cbtt_gan_nhat="07/2026"),
        gtvh_f_value=None,
    )
    assert not r.passed
    assert r.thieu_du_lieu is False
    assert "07/2026" in r.message
    assert "3.2" in r.message or "3.3" in r.message or "3.4" in r.message


def test_thieu_ngay_niem_yet_thi_danh_dau_thieu_du_lieu():
    r = screen_eligibility(_stock(listing_date=None), AS_OF, gtvh_rank=100)
    assert not r.passed
    assert r.thieu_du_lieu is True


def test_niem_yet_duoi_6_thang_khong_phai_thieu_du_lieu():
    """Co ngay niem yet ro rang, chi la chua du thang - day la truot THUC CHAT."""
    r = screen_eligibility(_stock(listing_date=date(2026, 4, 1)), AS_OF, gtvh_rank=100)
    assert not r.passed
    assert r.thieu_du_lieu is False


def test_turnover_khong_tinh_duoc_do_thieu_free_float_la_thieu_du_lieu():
    r = screen_liquidity(_stock(free_float=None), None)
    assert not r.passed
    assert r.thieu_du_lieu is True


def test_turnover_that_khong_dat_khong_phai_thieu_du_lieu():
    r = screen_liquidity(_stock(in_previous_basket=False), 0.00049)
    assert not r.passed
    assert r.thieu_du_lieu is False


def test_thieu_lnst_thi_danh_dau_thieu_du_lieu():
    r = screen_profit(_stock(lnst_positive=None))
    assert not r.passed
    assert r.thieu_du_lieu is True


def test_lnst_am_khong_phai_thieu_du_lieu():
    r = screen_profit(_stock(lnst_positive=False))
    assert not r.passed
    assert r.thieu_du_lieu is False
