import logging

import pytest

import collectors.market_data as md
from collectors.market_data import DieuTietRequest


def _fake_clock(start=0.0):
    """Dong ho gia: tra ve mot list [thoi_gian_hien_tai] co the chinh tay trong test."""
    return [start]


def test_duoi_gioi_han_khong_ngu(monkeypatch):
    monkeypatch.setenv(md.ENV_TAT_THROTTLE, "0")
    dong_ho = _fake_clock(0.0)
    so_lan_ngu = []
    dt = DieuTietRequest(gioi_han=3, cua_so=60, time_fn=lambda: dong_ho[0], sleep_fn=so_lan_ngu.append)

    dt.cho_phep()
    dong_ho[0] += 1
    dt.cho_phep()
    dong_ho[0] += 1
    dt.cho_phep()

    assert so_lan_ngu == [], "Duoi gioi han thi khong duoc ngu lan nao"


def test_vuot_gioi_han_thi_ngu_du_de_moc_cu_rot_khoi_cua_so(monkeypatch):
    monkeypatch.setenv(md.ENV_TAT_THROTTLE, "0")
    dong_ho = _fake_clock(0.0)
    so_lan_ngu = []
    dt = DieuTietRequest(gioi_han=2, cua_so=60, time_fn=lambda: dong_ho[0], sleep_fn=so_lan_ngu.append)

    dt.cho_phep()  # t=0
    dong_ho[0] = 5
    dt.cho_phep()  # t=5, du 2 request trong cua so

    dong_ho[0] = 10
    dt.cho_phep()  # t=10, request thu 3 -> vuot gioi han, phai ngu

    assert len(so_lan_ngu) == 1
    # Moc cu nhat la t=0, cua so 60s -> phai ngu toi thieu 50s de moc do rot ra
    assert so_lan_ngu[0] == pytest.approx(50.0)


def test_goi_tu_cache_khong_tinh_vao_gioi_han(tmp_path, monkeypatch, caplog):
    """Goi lai nhieu lan trong ngay (lay tu cache) khong duoc sinh lan ngu nao."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("VN30_TRACKER_KHONG_THROTTLE", "0")
    so_lan_ngu = []
    monkeypatch.setattr(md._throttle, "sleep_fn", so_lan_ngu.append)
    monkeypatch.setattr(md._throttle, "gioi_han", 1)  # gioi han rat thap de de phat hien neu bi tinh nham

    from types import SimpleNamespace
    import pandas as pd

    dem = {"n": 0}

    class FakeListing:
        def symbols_by_exchange(self):
            dem["n"] += 1
            return pd.DataFrame({
                "symbol": ["vic"], "exchange": ["HOSE"], "type": ["stock"],
            })

    monkeypatch.setitem(__import__("sys").modules, "vnstock", SimpleNamespace(Listing=FakeListing))

    md.fetch_hose_universe()
    md.fetch_hose_universe()
    md.fetch_hose_universe()

    assert dem["n"] == 1, "Chi goi mang 1 lan, con lai tu cache"
    assert so_lan_ngu == [], "Cache hit khong duoc di qua throttle nen khong ngu"


def test_cua_so_truot_dung_sau_khi_qua_60_giay(monkeypatch):
    monkeypatch.setenv(md.ENV_TAT_THROTTLE, "0")
    dong_ho = _fake_clock(0.0)
    so_lan_ngu = []
    dt = DieuTietRequest(gioi_han=1, cua_so=60, time_fn=lambda: dong_ho[0], sleep_fn=so_lan_ngu.append)

    dt.cho_phep()  # t=0
    dong_ho[0] = 61  # qua cua so 60s, moc cu phai bi loai
    dt.cho_phep()  # khong duoc ngu vi moc t=0 da roi khoi cua so

    assert so_lan_ngu == []


def test_log_info_khi_ngu(monkeypatch, caplog):
    monkeypatch.setenv(md.ENV_TAT_THROTTLE, "0")
    dong_ho = _fake_clock(0.0)
    dt = DieuTietRequest(gioi_han=1, cua_so=60, time_fn=lambda: dong_ho[0], sleep_fn=lambda s: None)

    dt.cho_phep()  # t=0
    dong_ho[0] = 1
    with caplog.at_level(logging.INFO):
        dt.cho_phep()  # vuot gioi han -> phai log INFO

    assert "INFO" in caplog.text or any(r.levelname == "INFO" for r in caplog.records)
    assert any("giây" in r.message or "giay" in r.message for r in caplog.records)


def test_doc_gioi_han_request_tu_env_mac_dinh_khi_khong_set(monkeypatch):
    monkeypatch.delenv(md.ENV_GIOI_HAN_REQUEST, raising=False)
    assert md._doc_gioi_han_request_tu_env() == 55


def test_doc_gioi_han_request_tu_env_doc_duoc_gia_tri_set(monkeypatch):
    monkeypatch.setenv(md.ENV_GIOI_HAN_REQUEST, "15")
    assert md._doc_gioi_han_request_tu_env() == 15


def test_doc_gioi_han_request_tu_env_gia_tri_khong_hop_le_roi_ve_mac_dinh(monkeypatch):
    monkeypatch.setenv(md.ENV_GIOI_HAN_REQUEST, "abc")
    assert md._doc_gioi_han_request_tu_env() == 55


# ---------------------------------------------------------------------------
# Moi ham cham mang phai goi _throttle.cho_phep() DUNG 1 LAN cho MOI request
# THAT ra mang - khong it hon (request "lot luoi"), khong nhieu hon (ngu oan).
# Cac test nay TIEM ham gia, dem so lan cho_phep() duoc goi, KHONG goi mang
# that va KHONG ngu that (tat throttle qua fixture autouse trong conftest.py,
# o day ta thay the han cho_phep bang bo dem).
# ---------------------------------------------------------------------------

from datetime import date
from types import SimpleNamespace

import pandas as pd


def _dem_throttle(monkeypatch):
    so_lan = {"n": 0}
    monkeypatch.setattr(md._throttle, "cho_phep", lambda: so_lan.__setitem__("n", so_lan["n"] + 1))
    return so_lan


def test_fetch_hose_universe_goi_throttle_dung_1_lan(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    so_lan = _dem_throttle(monkeypatch)

    class FakeListing:
        def symbols_by_exchange(self):
            return pd.DataFrame({"symbol": ["vic"], "exchange": ["HOSE"], "type": ["stock"]})

    monkeypatch.setitem(__import__("sys").modules, "vnstock", SimpleNamespace(Listing=FakeListing))

    md.fetch_hose_universe()
    assert so_lan["n"] == 1


def test_fetch_daily_goi_throttle_dung_1_lan_moi_request(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    so_lan = _dem_throttle(monkeypatch)
    raw = pd.DataFrame({"time": ["2026-01-05"], "close": [10.0], "volume": [100]})

    class FakeQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval):
            return raw

    monkeypatch.setitem(__import__("sys").modules, "vnstock", SimpleNamespace(Quote=FakeQuote))

    md.fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    assert so_lan["n"] == 1, "1 lan goi mang that (cache mien) -> dung 1 lan throttle"

    md.fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    assert so_lan["n"] == 1, "Lan hai la cache hit, khong duoc goi throttle them"


def test_fetch_shares_outstanding_goi_throttle_dung_1_lan_moi_lo(tmp_path, monkeypatch):
    """Danh sach ma dai hon 1 lo (BATCH_SIZE_SHARES) phai dem throttle theo TUNG lo,
    khong phai 1 lan cho ca ham (moi lo la 1 request price_board that ra mang)."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "BATCH_SIZE_SHARES", 2)
    so_lan = _dem_throttle(monkeypatch)

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            return pd.DataFrame({
                "listing_symbol": symbols_list,
                "listing_listed_share": [1000] * len(symbols_list),
            })

    monkeypatch.setitem(__import__("sys").modules, "vnstock", SimpleNamespace(Trading=FakeTrading))

    md.fetch_shares_outstanding(["A", "B", "C", "D", "E"])  # 5 ma, lo=2 -> 3 lo
    assert so_lan["n"] == 3


def test_fetch_lnst_goi_throttle_2_lan_khi_phai_roi_ve_bao_cao_nam(tmp_path, monkeypatch):
    """fetch_lnst goi API 2 lan (quy roi nam) khi thieu du lieu ban nien - moi lan
    phai qua throttle rieng, khong duoc gop chung thanh 1 lan."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))
    so_lan = _dem_throttle(monkeypatch)

    df_nam = pd.DataFrame({
        "item": ["attributable_to_parent_company"],
        "item_en": ["attributable_to_parent_company"],
        "item_id": ["attributable_to_parent_company"],
        "2025": [123],
    })
    df_quy_rong = pd.DataFrame(columns=["item", "item_en", "item_id"])

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            return df_quy_rong if period == "quarter" else df_nam

    monkeypatch.setitem(__import__("sys").modules, "vnstock", SimpleNamespace(Finance=FakeFinance))

    kq = md.fetch_lnst("FPT")
    assert kq is not None and kq["lnst_vnd"] == 123
    assert so_lan["n"] == 2, "Phai dem ca 2 lan goi API (quy that bai + nam thanh cong)"


def test_vnstock_khong_con_retry_ngam_moi_lan_thu_deu_qua_throttle():
    """Kiem tra fix nguyen nhan #2: tenacity.retry() ma vnstock dung da bi thay
    the (o dau collectors/market_data.py) thanh 'chi thu dung 1 lan', de khong
    con request nao am tham 'lot luoi' qua _throttle nhu truoc."""
    import tenacity

    dinh_nghia = tenacity.retry(stop=tenacity.stop_after_attempt(5))
    # Ham gia luon nem loi - neu retry that su chi 1 lan thi chi bi goi 1 lan.
    so_lan_goi = {"n": 0}

    @dinh_nghia
    def luon_loi():
        so_lan_goi["n"] += 1
        raise RuntimeError("gia lap loi mang")

    with pytest.raises(tenacity.RetryError):
        luon_loi()
    assert so_lan_goi["n"] == 1, "tenacity.retry() phai da bi ep ve stop_after_attempt(1)"
