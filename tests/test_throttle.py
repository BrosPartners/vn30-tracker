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
