from datetime import date

import pandas as pd

from rules.basket import build_vn30
from rules.models import StockInput

AS_OF = date(2026, 7, 1)
TIMES = pd.to_datetime(["2026-01-05", "2026-02-05", "2026-03-05"])


def make(symbol, close, volume=1_000_000, shares=1_000_000_000, free_float=0.5,
         in_basket=False, lnst=True, listing=date(2015, 1, 1)):
    return StockInput(
        symbol=symbol,
        daily=pd.DataFrame({"time": TIMES, "close": [close] * 3, "volume": [volume] * 3}),
        shares_outstanding=shares,
        listing_date=listing,
        free_float=free_float,
        in_previous_basket=in_basket,
        lnst_positive=lnst,
        audit_opinion="unqualified",
    )


def _universe(n=45):
    """n ma, ma thu i co gia giam dan -> von hoa giam dan, thu hang on dinh."""
    return [make(f"S{i:02d}", close=100.0 - i) for i in range(n)]


def test_chon_dung_30_ma():
    r = build_vn30(_universe(), AS_OF)
    assert len(r.constituents) == 30


def test_top_20_von_hoa_luon_duoc_chon():
    r = build_vn30(_universe(), AS_OF)
    for i in range(20):
        assert f"S{i:02d}" in r.constituents


def test_hang_21_40_uu_tien_ma_trong_ro_ky_truoc():
    """S30 nam trong ro ky truoc, S21 thi khong -> S30 duoc chon truoc du von hoa thap hon."""
    u = _universe()
    for s in u:
        if s.symbol == "S30":
            s.in_previous_basket = True
    r = build_vn30(u, AS_OF)
    assert "S30" in r.constituents


def test_danh_sach_du_phong_la_5_ma_gtvh_lon_nhat_con_lai():
    r = build_vn30(_universe(), AS_OF)
    assert len(r.reserve) == 5
    assert not set(r.reserve) & set(r.constituents)


def test_ma_lnst_am_bi_loai():
    u = _universe()
    u[0].lnst_positive = False
    r = build_vn30(u, AS_OF)
    assert "S00" not in r.constituents
    assert any(s.step == "profit" and not s.passed for s in r.screens["S00"])


def test_chua_xac_nhan_y_kien_kiem_toan_van_vao_ro_nhung_co_nhan_canh_bao():
    """Quyet dinh 2026-09-08: unknown khong tu loai, chi gan nhan."""
    u = _universe()
    u[3].audit_opinion = "unknown"
    r = build_vn30(u, AS_OF)
    assert "S03" in r.constituents
    buoc = next(s for s in r.screens["S03"] if s.step == "profit")
    assert buoc.passed
    assert "chưa xác nhận" in buoc.message.lower()
    assert r.metrics["S03"]["audit_opinion"] == "unknown"


def test_ma_klgd_duoi_300k_bi_loai():
    u = _universe()
    u[1].daily = u[1].daily.assign(volume=[299_000] * 3)
    r = build_vn30(u, AS_OF)
    assert "S01" not in r.constituents
    assert any(s.step == "vn30_liquidity" and not s.passed for s in r.screens["S01"])


def test_ma_thieu_free_float_bi_loai_va_duoc_liet_ke_rieng():
    u = _universe()
    u[2].free_float = None
    r = build_vn30(u, AS_OF)
    assert "S02" not in r.constituents
    assert "S02" in r.missing_data


def test_moi_ma_deu_co_ly_do_va_so_lieu():
    r = build_vn30(_universe(), AS_OF)
    for s in _universe():
        assert r.screens[s.symbol], f"{s.symbol} khong co ly do nao"
        assert r.metrics[s.symbol]["gtvh"] > 0
        assert "gtvh_rank" in r.metrics[s.symbol]


def test_thu_hang_gtvh_tinh_tren_toan_bo_vu_tru_khong_chi_ma_dat():
    """Ma S00 bi loai vi LNST am nhung van giu hang 1 ve von hoa."""
    u = _universe()
    u[0].lnst_positive = False
    r = build_vn30(u, AS_OF)
    assert r.metrics["S00"]["gtvh_rank"] == 1


# --- Dieu 4.3.1.b: danh sach xem xet bu cho du 50 ma ---

def _good(i):
    """Ma 'tot': gia cao, khoi luong lon -> vuot xa nguong GTGD_KL 30 ty."""
    return make(f"G{i:02d}", close=200.0 - i, volume=500_000)


def _borderline(i):
    """Ma 'ranh gioi': gia thap, KLGD dat 300k cp nhung GTGD_KL < 30 ty.

    volume tang dan theo i -> GTGD_KL tang dan theo i (i lon nhat = GTGD_KL cao nhat).
    """
    return make(f"B{i:02d}", close=50.0, volume=300_000 + i * 1_000)


def test_bu_ma_gtgd_kl_cao_nhat_khi_thieu_50_ma_dat_nguong():
    """25 ma tot + 15 ma ranh gioi (deu duoi nguong 30 ty) -> can bu 5 ma
    de du 50 ma trong danh sach xem xet. 5 ma bu la 5 ma ranh gioi co GTGD_KL
    cao nhat (i = 10..14), va chung phai lot duoc vao ro vi tong "dat" = 30."""
    u = [_good(i) for i in range(25)] + [_borderline(i) for i in range(15)]
    r = build_vn30(u, AS_OF)
    # 5 ma ranh gioi GTGD_KL cao nhat (B10..B14) duoc bu vao va lot ro
    for i in range(10, 15):
        assert f"B{i:02d}" in r.constituents, f"B{i:02d} phai duoc bu va vao ro"
    # 10 ma ranh gioi GTGD_KL thap nhat (B00..B09) KHONG duoc bu
    for i in range(0, 10):
        assert f"B{i:02d}" not in r.constituents


def test_ma_duoc_bu_co_screen_result_passed_va_thong_bao_bu():
    u = [_good(i) for i in range(25)] + [_borderline(i) for i in range(15)]
    r = build_vn30(u, AS_OF)
    buoc = next(s for s in r.screens["B14"] if s.step == "vn30_liquidity")
    assert buoc.passed
    assert "bù" in buoc.message.lower() or "50" in buoc.message


def test_khong_bu_them_ma_khi_da_du_50_ma_dat_nguong():
    """Vu tru mac dinh 50 ma deu vuot nguong 30 ty -> khong co thong bao bu nao."""
    r = build_vn30(_universe(50), AS_OF)
    for buoc_list in r.screens.values():
        for b in buoc_list:
            if b.step == "vn30_liquidity":
                assert "bù" not in b.message.lower()


def test_dong_hang_gtvh_uu_tien_gtgd_kl_lon_hon():
    """2 ma cung GTVH (gia va so luong CP giong nhau) nhung khac GTGD_KL
    (khac volume) -> ma GTGD_KL lon hon phai duoc xep hang gtvh tot hon (so nho hon)."""
    cao = make("TIE_CAO", close=100.0, volume=800_000)
    thap = make("TIE_THAP", close=100.0, volume=500_000)
    r = build_vn30([cao, thap], AS_OF)
    assert r.metrics["TIE_CAO"]["gtvh"] == r.metrics["TIE_THAP"]["gtvh"]
    assert r.metrics["TIE_CAO"]["gtgd_kl"] > r.metrics["TIE_THAP"]["gtgd_kl"]
    assert r.metrics["TIE_CAO"]["gtvh_rank"] < r.metrics["TIE_THAP"]["gtvh_rank"]


def test_ro_duoi_30_ma_thi_co_canh_bao():
    r = build_vn30(_universe(10), AS_OF)
    assert len(r.constituents) < 30
    assert r.canh_bao
    assert any("30" in c for c in r.canh_bao)


def test_ro_du_30_ma_thi_khong_co_canh_bao():
    r = build_vn30(_universe(45), AS_OF)
    assert len(r.constituents) == 30
    assert r.canh_bao == []
