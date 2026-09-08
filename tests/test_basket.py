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
