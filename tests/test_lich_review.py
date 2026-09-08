from datetime import date

from rules.lich_review import ky_review_ke_tiep, thu_tu_trong_thang


def test_thu_tu_tuan_thu_ba():
    """Thu Tu tuan thu 3 cua thang 7/2026 la ngay 15."""
    assert thu_tu_trong_thang(2026, 7, 3) == date(2026, 7, 15)
    assert thu_tu_trong_thang(2026, 1, 3) == date(2026, 1, 21)


def test_thu_hai_dau_tien_lam_ngay_hieu_luc():
    """Ky thang 7 co hieu luc thu Hai dau tien cua thang 8/2026 = ngay 3."""
    k = ky_review_ke_tiep(date(2026, 6, 1))
    assert k["ky"] == "07/2026"
    assert k["ngay_chot"] == date(2026, 7, 15)
    assert k["ngay_hieu_luc"] == date(2026, 8, 3)


def test_qua_ky_thang_7_thi_nhay_sang_thang_1_nam_sau():
    k = ky_review_ke_tiep(date(2026, 9, 8))
    assert k["ky"] == "01/2027"
    assert k["ngay_chot"] == date(2027, 1, 20)


def test_hom_nay_2026_09_08_ky_ke_tiep_la_01_2027():
    """Bao ve loi da fix: build.py tung hard-code '07/2026' du ky do da dien ra
    (cong bo 15/07/2026, hieu luc 03/08/2026). Ky ke tiep THAT phai la 01/2027."""
    k = ky_review_ke_tiep(date(2026, 9, 8))
    assert k["ky"] == "01/2027"
