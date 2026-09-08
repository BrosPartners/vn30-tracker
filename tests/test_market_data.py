import logging
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

import collectors.market_data as md
from collectors.market_data import (
    chuan_hoa_daily,
    cached,
    fetch_daily,
    fetch_daily_batch,
    fetch_hose_universe,
    fetch_shares_outstanding,
)


def test_chuan_hoa_daily_giu_dung_ba_cot():
    raw = pd.DataFrame({
        "time": ["2026-01-05", "2026-01-06"],
        "open": [1.0, 2.0], "high": [1.0, 2.0], "low": [1.0, 2.0],
        "close": [10.0, 11.0], "volume": [100, 200],
    })
    df = chuan_hoa_daily(raw)
    assert list(df.columns) == ["time", "close", "volume"]
    assert pd.api.types.is_datetime64_any_dtype(df["time"])


def test_chuan_hoa_daily_bo_phien_khoi_luong_rong():
    """Phien khong khop lenh lam lech trung vi -> phai bo."""
    raw = pd.DataFrame({
        "time": ["2026-01-05", "2026-01-06"],
        "close": [10.0, 11.0], "volume": [0, 200],
    })
    assert len(chuan_hoa_daily(raw)) == 1


def test_chuan_hoa_daily_thieu_cot_thi_bao_loi():
    with pytest.raises(ValueError, match="volume"):
        chuan_hoa_daily(pd.DataFrame({"time": ["2026-01-05"], "close": [10.0]}))


def test_cache_chi_goi_ham_that_mot_lan(tmp_path):
    dem = {"n": 0}

    def that():
        dem["n"] += 1
        return {"gia_tri": 42}

    k = "thu"
    assert cached(that, k, tmp_path)["gia_tri"] == 42
    assert cached(that, k, tmp_path)["gia_tri"] == 42
    assert dem["n"] == 1, "Lan hai phai lay tu cache"


def test_cache_tach_theo_ngay(tmp_path):
    """File cache mang ten ngay -> sang hom sau tu dong lay lai."""
    cached(lambda: {"x": 1}, "thu", tmp_path)
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert date.today().isoformat() in files[0].name


# ---------------------------------------------------------------------------
# Sua 1: cac ham fetch tu noi cache, khoa sinh tu tham so
# ---------------------------------------------------------------------------

def test_fetch_hose_universe_dung_cache_lan_hai_khong_goi_lai(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    dem = {"n": 0}

    class FakeListing:
        def symbols_by_exchange(self):
            dem["n"] += 1
            return pd.DataFrame({
                "symbol": ["vic", "vcb"],
                "exchange": ["HOSE", "HOSE"],
                "type": ["stock", "stock"],
            })

    fake_vnstock = SimpleNamespace(Listing=FakeListing)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq1 = fetch_hose_universe()
    kq2 = fetch_hose_universe()
    assert kq1 == kq2 == ["VCB", "VIC"]
    assert dem["n"] == 1, "Lan hai phai lay tu cache"
    files = list(tmp_path.glob("hose-universe-*.json"))
    assert len(files) == 1


def test_fetch_daily_dung_cache_lan_hai_khong_goi_mang(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    dem = {"n": 0}
    raw = pd.DataFrame({
        "time": ["2026-01-05", "2026-01-06"],
        "close": [10.5, 11.2], "volume": [100, 200],
    })

    class FakeQuote:
        def __init__(self, symbol, source):
            self.symbol = symbol

        def history(self, start, end, interval):
            dem["n"] += 1
            return raw

    fake_vnstock = SimpleNamespace(Quote=FakeQuote)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    df1 = fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    df2 = fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    assert dem["n"] == 1, "Lan hai phai lay tu cache, khong goi mang"
    assert pd.api.types.is_datetime64_any_dtype(df2["time"])
    assert pd.api.types.is_numeric_dtype(df2["close"])
    assert pd.api.types.is_numeric_dtype(df2["volume"])
    pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))


def test_fetch_daily_khoa_cache_gom_ca_symbol_start_end(tmp_path, monkeypatch):
    """Hai lan goi khac tham so khong duoc dung chung 1 file cache."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    raw = pd.DataFrame({"time": ["2026-01-05"], "close": [10.0], "volume": [100]})

    class FakeQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval):
            return raw

    fake_vnstock = SimpleNamespace(Quote=FakeQuote)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    fetch_daily("VCB", date(2026, 1, 1), date(2026, 1, 10))
    fetch_daily("VIC", date(2026, 2, 1), date(2026, 2, 10))
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 3


def test_fetch_shares_outstanding_khoa_theo_danh_sach_ma(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    dem = {"n": 0}

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            dem["n"] += 1
            return pd.DataFrame({
                "listing_symbol": symbols_list,
                "listing_listed_share": [1000] * len(symbols_list),
            })

    fake_vnstock = SimpleNamespace(Trading=FakeTrading)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq1 = fetch_shares_outstanding(["VIC", "VCB"])
    kq2 = fetch_shares_outstanding(["VCB", "VIC"])  # thu tu khac, cung tap hop
    assert dem["n"] == 1, "Danh sach ma giong nhau (chi khac thu tu) phai trung khoa cache"
    assert kq1 == kq2

    fetch_shares_outstanding(["VIC", "VCB", "VNM"])
    assert dem["n"] == 2, "Danh sach ma khac nhau phai la khoa cache khac"


# ---------------------------------------------------------------------------
# Sua 2: fetch_daily_batch phai nem loi khi ty le ma loi vuot nguong
# ---------------------------------------------------------------------------

def test_fetch_daily_batch_duoi_nguong_tra_ket_qua():
    du_lieu = pd.DataFrame({"time": pd.to_datetime(["2026-01-05"]), "close": [10.0], "volume": [100]})
    rong = pd.DataFrame(columns=["time", "close", "volume"])

    def fetch_gia(symbol, start, end):
        if symbol == "LOI":
            return rong
        return du_lieu

    symbols = ["A", "B", "C", "LOI"]  # 1/4 = 25% < 30%
    kq = fetch_daily_batch(symbols, date(2026, 1, 1), date(2026, 1, 10), nguong_loi=0.3, fetch_fn=fetch_gia)
    assert set(kq.keys()) == {"A", "B", "C", "LOI"}
    assert kq["LOI"].empty
    assert not kq["A"].empty


def test_fetch_daily_batch_tren_nguong_nem_loi():
    rong = pd.DataFrame(columns=["time", "close", "volume"])

    def fetch_gia_loi_het(symbol, start, end):
        return rong

    symbols = ["A", "B", "C", "D"]
    with pytest.raises(RuntimeError, match="lỗi"):
        fetch_daily_batch(symbols, date(2026, 1, 1), date(2026, 1, 10), nguong_loi=0.3, fetch_fn=fetch_gia_loi_het)


# ---------------------------------------------------------------------------
# Sua 3: log phai du de nguoi van hanh hanh dong
# ---------------------------------------------------------------------------

def test_fetch_shares_outstanding_log_ten_ma_khi_bo_vi_gia_tri_khong_hop_le(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            return pd.DataFrame({
                "listing_symbol": ["VIC", "VCB"],
                "listing_listed_share": [1000, 0],
            })

    fake_vnstock = SimpleNamespace(Trading=FakeTrading)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    with caplog.at_level(logging.WARNING):
        kq = fetch_shares_outstanding(["VIC", "VCB"])
    assert "VIC" in kq and "VCB" not in kq
    assert "VCB" in caplog.text


def test_fetch_shares_outstanding_log_ma_thieu_trong_ket_qua(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            return pd.DataFrame({
                "listing_symbol": ["VIC"],
                "listing_listed_share": [1000],
            })

    fake_vnstock = SimpleNamespace(Trading=FakeTrading)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    with caplog.at_level(logging.WARNING):
        fetch_shares_outstanding(["VIC", "VNM"])
    assert "VNM" in caplog.text


def test_fetch_shares_outstanding_log_danh_sach_ma_khi_lo_loi(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            raise RuntimeError("timeout")

    fake_vnstock = SimpleNamespace(Trading=FakeTrading)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    with caplog.at_level(logging.WARNING):
        fetch_shares_outstanding(["VIC", "VCB"])
    assert "VIC" in caplog.text and "VCB" in caplog.text


def test_chuan_hoa_daily_log_so_phien_bi_loai(caplog):
    raw = pd.DataFrame({
        "time": ["2026-01-05", "2026-01-06"],
        "close": [10.0, 11.0], "volume": [0, 200],
    })
    with caplog.at_level(logging.WARNING):
        chuan_hoa_daily(raw)
    assert "1" in caplog.text


def test_chuan_hoa_daily_khong_log_neu_khong_co_phien_bi_loai(caplog):
    raw = pd.DataFrame({
        "time": ["2026-01-05", "2026-01-06"],
        "close": [10.0, 11.0], "volume": [100, 200],
    })
    with caplog.at_level(logging.WARNING):
        chuan_hoa_daily(raw)
    assert caplog.text == ""


# ---------------------------------------------------------------------------
# Sua 4: hang so thay hard-code
# ---------------------------------------------------------------------------

def test_hang_so_da_duoc_khai_bao():
    assert md.BATCH_SIZE_SHARES == 50
    assert md.HOSE_EXCHANGES == ["HOSE", "HSX"]
    assert isinstance(md.VNSTOCK_SOURCE, str) and md.VNSTOCK_SOURCE
