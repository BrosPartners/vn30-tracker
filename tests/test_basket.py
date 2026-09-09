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
    """25 mã tốt đạt ngưỡng 30 tỷ + 15 mã ranh giới dưới ngưỡng -> thiếu 25 mã để đủ 50.

    Pool ứng viên bù chỉ có 15 mã, nên cả 15 đều được bù vào danh sách xem xét (đủ 50).
    Tuy nhiên sau đó bước f cắt xuống còn 30 mã theo thứ hạng GTVH, nên chỉ 5 mã ranh giới
    có GTGD_KL cao nhất (B10..B14) sống sót trong rổ (cắt tiêu vào không phải do bù dừng).
    """
    u = [_good(i) for i in range(25)] + [_borderline(i) for i in range(15)]
    r = build_vn30(u, AS_OF)
    # 5 mã ranh giới GTGD_KL cao nhất (B10..B14) được bù vào danh sách xem xét và sống sót qua cắt bước f
    for i in range(10, 15):
        assert f"B{i:02d}" in r.constituents, f"B{i:02d} phải được bù và vào rổ"
    # 10 mã ranh giới GTGD_KL thấp nhất (B00..B09) không được bù (bị cắt bước f vì thứ hạng GTVH thấp)
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


def test_chu_ly_cat_dung_so_luong_khi_bu_vao_danh_sach_xem_xet():
    """Kiểm chứng rằng khi pool ứng viên bù LỚN HƠN số còn thiếu, phần dư bị loại đúng.

    48 mã tốt đạt ngưỡng 30 tỷ (thiếu 2 mã cho đủ 50), pool bù có 6 mã với GTGD_KL
    khác nhau rõ rệt. Chỉ 2 mã GTGD_KL cao nhất được bù vào danh sách xem xét,
    có ScreenResult bước vn30_liquidity.b với passed=True; 4 mã còn lại vẫn passed=False
    không được bù (giữ failed từ bước .b).
    """
    # 48 mã tốt: đủ cao để đạt ngưỡng
    goods = [make(f"G{i:02d}", close=200.0 - i, volume=500_000) for i in range(48)]

    # 6 mã ranh giới: tất cả dưới ngưỡng 30 tỷ, GTGD_KL khác nhau rõ rệt
    # Điều kiện cân bằng:
    # - KLGD_KL >= 300k (bước a)
    # - GTGD_KL < 30 tỷ (bước b)
    # - Turnover >= 0.0005 (liquidity) để vượt qua trước bước vn30_liquidity
    # Sử dụng close=100:
    # - GTVH = 100 * 1e9 * 1000 = 100e12, GTVH_f = 50e12
    # - Turnover >= 0.0005 => GTGD_KL >= 50e9 = 50 tỷ (mâu thuẫn với GTGD_KL < 30!)
    # Vậy dùng close cao hơn để GTVH cao hơn, giảm yêu cầu GTGD_KL:
    # - close=300: GTVH = 300e12, GTVH_f = 150e12
    # - Turnover >= 0.0005 => GTGD_KL >= 75e9 = 75 tỷ (vẫn mâu thuẫn!)
    # => Cách duy nhất: giảm turnover ngưỡng. Xem lại: min_turnover_existing = 0.0004 (0,04%)
    # Với mã trong rổ cũ (in_previous_basket=True):
    # - Turnover >= 0.0004 => GTGD_KL >= 40e9 = 40 tỷ (close=100, vẫn > 30)
    # Vậy dùng close=50 và in_previous_basket=True:
    # - GTVH = 50e12, GTVH_f = 25e12, Turnover >= 0.0004 => GTGD_KL >= 10e9
    # - GTGD_KL ở 10-29.9 tỷ => volume ở 200k-599k (KLGD_KL ở 200k-599k, >= 300k ✓)
    borderlines = [
        make("B00", close=50.0, volume=300_000, in_basket=True),   # GTGD = 15 tỷ, Turnover = 0.06%
        make("B01", close=50.0, volume=340_000, in_basket=True),   # GTGD = 17 tỷ, Turnover = 0.068%
        make("B02", close=50.0, volume=380_000, in_basket=True),   # GTGD = 19 tỷ, Turnover = 0.076%
        make("B03", close=50.0, volume=420_000, in_basket=True),   # GTGD = 21 tỷ, Turnover = 0.084%
        make("B04", close=50.0, volume=460_000, in_basket=True),   # GTGD = 23 tỷ, Turnover = 0.092%
        make("B05", close=50.0, volume=499_000, in_basket=True),   # GTGD = 24.95 tỷ, Turnover = 0.0998%
    ]
    u = goods + borderlines
    r = build_vn30(u, AS_OF)

    # Đúng 2 mã GTGD_KL cao nhất (B05, B04) được bù vào danh sách xem xét
    # Kiểm chứng ScreenResult bước vn30_liquidity có passed=True và có thông báo bù
    for symbol in ["B05", "B04"]:
        screen_step = next(s for s in r.screens[symbol] if s.step == "vn30_liquidity")
        assert screen_step.passed, f"{symbol} phải có ScreenResult passed=True sau bù"
        assert "bù" in screen_step.message.lower() or "50" in screen_step.message, \
            f"{symbol} ScreenResult phải có thông báo bù"

    # 4 mã còn lại trong pool không được bù, ScreenResult bước vn30_liquidity vẫn passed=False
    for symbol in ["B00", "B01", "B02", "B03"]:
        screen_step = next(s for s in r.screens[symbol] if s.step == "vn30_liquidity")
        assert not screen_step.passed, f"{symbol} phải có ScreenResult passed=False (không được bù)"
        # Thông báo phải nói "thiếu" hoặc "dưới ngưỡng" (vẫn failed, không được bù)
        assert ("thiếu" in screen_step.message.lower() or "dưới" in screen_step.message.lower()), \
            f"{symbol} thông báo phải nói 'thiếu' hoặc 'dưới ngưỡng'"


def test_canh_bao_khi_ma_thieu_du_lieu_co_hang_von_hoa_du_dieu_kien():
    """S02 (hang 3, <=40) thieu free_float -> phai co canh bao noi ro ten ma va
    ly do (thieu du lieu, khong phai truot thuc chat), de nguoi doc khong hieu
    lam ro du kien la dang tin cay hoan toan."""
    u = _universe()
    u[2].free_float = None
    r = build_vn30(u, AS_OF)
    assert any("S02" in cb for cb in r.canh_bao), r.canh_bao
    canh_bao_s02 = next(cb for cb in r.canh_bao if "S02" in cb)
    assert "thiếu dữ liệu" in canh_bao_s02.lower()
    assert "không nên" in canh_bao_s02.lower() or "không đáng tin" in canh_bao_s02.lower()


def test_khong_canh_bao_khi_ma_thieu_du_lieu_hang_thap_ngoai_vung_chon():
    """Ma thieu du lieu nhung hang > 40 (ngoai vung duoc chon) thi khong can canh
    bao rieng vi khong anh huong toi viec chon ro."""
    u = _universe()
    u[44].free_float = None  # S44, hang 45 - ngoai vung 40
    r = build_vn30(u, AS_OF)
    assert not any("S44" in cb for cb in r.canh_bao)


# ---------------------------------------------------------------------------
# Pham vi "thieu du lieu": LNST chi duoc lay cho danh sach xem xet (top 50).
# Ma hang > 50 khong the vao ro theo Dieu 4.3.1.f (chi xet den hang 40), nen
# viec KHONG goi BCTC cho nhung ma do la quyet dinh pham vi co y, khong phai
# lo hong du lieu - gan nhan "thieu du lieu" cho chung lam nguoi doc hieu sai
# rang cong cu con nhieu cho mu.
# ---------------------------------------------------------------------------

def test_thieu_lnst_o_hang_ngoai_danh_sach_xem_xet_khong_phai_thieu_du_lieu():
    ds = _universe(60)
    ds[55] = make("S55", close=100.0 - 55, lnst=None)
    r = build_vn30(ds, AS_OF)
    assert r.metrics["S55"]["gtvh_rank"] > 50
    assert "S55" not in r.missing_data


def test_thieu_lnst_o_hang_trong_danh_sach_xem_xet_van_la_thieu_du_lieu():
    ds = _universe(60)
    ds[10] = make("S10", close=100.0 - 10, lnst=None)
    r = build_vn30(ds, AS_OF)
    assert r.metrics["S10"]["gtvh_rank"] <= 50
    assert "S10" in r.missing_data


def test_thieu_free_float_o_hang_ngoai_danh_sach_xem_xet_van_la_thieu_du_lieu():
    """Free float lay tu cong bo HOSE cho TOAN BO VNAllshare - thieu la thieu that,
    khong phai do ta co tinh khong lay (khac LNST)."""
    ds = _universe(60)
    ds[55] = make("S55", close=100.0 - 55, free_float=None)
    r = build_vn30(ds, AS_OF)
    assert "S55" in r.missing_data
