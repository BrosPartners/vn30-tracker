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
    fetch_current_market_cap,
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
    # Ca 3 cua so nay deu la QUA KHU da chot (truoc ngay chay test that) nen
    # roi vao cache bat bien o thu muc con lichsu/ (xem cached() trong market_data.py).
    files = list(tmp_path.glob("**/*.json"))
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
# fetch_current_market_cap: sang thu von hoa HIEN TAI bang 1 luot goi price_board
# re, dung de xep hang toan san truoc khi chi lay lich su gia cho top N ma.
# ---------------------------------------------------------------------------

def test_fetch_current_market_cap_tinh_dung_va_khoa_theo_danh_sach_ma(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    dem = {"n": 0}

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            dem["n"] += 1
            return pd.DataFrame({
                "listing_symbol": symbols_list,
                "listing_listed_share": [1000, 2000][: len(symbols_list)],
                "match_match_price": [100, 200][: len(symbols_list)],
            })

    fake_vnstock = SimpleNamespace(Trading=FakeTrading)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq1 = fetch_current_market_cap(["VIC", "VCB"])
    assert kq1["VIC"] == 1000 * 100
    assert kq1["VCB"] == 2000 * 200

    kq2 = fetch_current_market_cap(["VCB", "VIC"])
    assert dem["n"] == 1, "Danh sach ma giong nhau (chi khac thu tu) phai trung khoa cache"
    assert kq1 == kq2


def test_fetch_current_market_cap_roi_ve_ref_price_khi_chua_khop_lenh(tmp_path, monkeypatch):
    """Ma chua co lenh khop trong phien (match_match_price = 0/None) -> dung gia tham
    chieu (listing_ref_price) de khong bo sot ma khoi buoc sang thu."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)

    class FakeTrading:
        def __init__(self, source, show_log):
            pass

        def price_board(self, symbols_list):
            return pd.DataFrame({
                "listing_symbol": ["VIC"],
                "listing_listed_share": [1000],
                "match_match_price": [0],
                "listing_ref_price": [50],
            })

    fake_vnstock = SimpleNamespace(Trading=FakeTrading)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq = fetch_current_market_cap(["VIC"])
    assert kq["VIC"] == 1000 * 50


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


# ---------------------------------------------------------------------------
# LNST tu dong (attributable_to_parent_company) - Dieu 3.1 + 4.3.1.d
# ---------------------------------------------------------------------------

def _df_bctc(item_ids, **cot_gia_tri):
    """Dung DataFrame gia lap dang vnstock: dong = chi tieu, cot = ky bao cao."""
    cols = {"item": item_ids, "item_en": item_ids, "item_id": item_ids}
    n = len(item_ids)
    for cot, gia_tri in cot_gia_tri.items():
        cols[cot] = gia_tri if isinstance(gia_tri, list) else [gia_tri] * n
    return pd.DataFrame(cols)


def test_fetch_lnst_boc_dung_chi_tieu_attributable_to_parent_va_uu_tien_ban_nien(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    df_quy = _df_bctc(
        ["net_profit", "attributable_to_parent_company"],
        **{"2026-Q2": [100, 50], "2026-Q1": [80, 40], "2025-Q4": [70, 30]},
    )

    class FakeFinance:
        def __init__(self, symbol, source):
            self.symbol = symbol

        def income_statement(self, period, lang):
            assert period == "quarter"
            return df_quy

    fake_vnstock = SimpleNamespace(Finance=FakeFinance)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq = md.fetch_lnst("FPT")
    assert kq is not None
    assert kq["lnst_vnd"] == 90  # 50 + 40 (Q1+Q2 2026)
    assert "bán niên" in kq["ky"].lower() or "Bán niên" in kq["ky"]
    assert "quý" in kq["ky"].lower() or "quy" in kq["nguon"].lower() or "quý" in kq["nguon"].lower()


def test_fetch_lnst_roi_ve_nam_gan_nhat_khi_thieu_du_ca_hai_quy(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    df_quy = _df_bctc(
        ["attributable_to_parent_company"],
        **{"2026-Q1": [40], "2025-Q4": [30]},  # thieu Q2/2026
    )
    df_nam = _df_bctc(
        ["attributable_to_parent_company"],
        **{"2025": [9_376_127_629_501], "2024": [8_000_000_000_000]},
    )

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            return df_quy if period == "quarter" else df_nam

    fake_vnstock = SimpleNamespace(Finance=FakeFinance)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq = md.fetch_lnst("FPT")
    assert kq["lnst_vnd"] == 9_376_127_629_501
    assert kq["ky"] == "Năm 2025"


def test_fetch_lnst_thieu_chi_tieu_thi_tra_none(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    df_rong = _df_bctc(["net_profit"], **{"2026-Q1": [1], "2026-Q2": [1], "2025": [1]})

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            return df_rong

    fake_vnstock = SimpleNamespace(Finance=FakeFinance)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    assert md.fetch_lnst("XYZ") is None


def test_fetch_lnst_loi_mang_thi_tra_none_khong_doan(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            raise RuntimeError("mất mạng")

    fake_vnstock = SimpleNamespace(Finance=FakeFinance)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    assert md.fetch_lnst("XYZ") is None


def test_fetch_lnst_dung_cache_lan_hai_khong_goi_lai(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))
    dem = {"n": 0}

    df_nam = _df_bctc(["attributable_to_parent_company"], **{"2025": [123]})
    df_quy_rong = _df_bctc(["attributable_to_parent_company"], **{"2026-Q1": [1]})

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            dem["n"] += 1
            return df_quy_rong if period == "quarter" else df_nam

    fake_vnstock = SimpleNamespace(Finance=FakeFinance)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    kq1 = md.fetch_lnst("FPT")
    kq2 = md.fetch_lnst("FPT")
    assert kq1 == kq2 == {"lnst_vnd": 123, "ky": "Năm 2025",
                          "nguon": "vnstock BCTC năm, attributable_to_parent_company"}
    assert dem["n"] == 2, "Lan hai phai lay tu cache (khong goi lai ca quarter lan year)"


def test_fetch_lnst_batch_duoi_nguong_tra_ket_qua():
    def fetch_gia(symbol):
        if symbol == "LOI":
            return None
        return {"lnst_vnd": 100, "ky": "Năm 2025", "nguon": "test"}

    kq = md.fetch_lnst_batch(["A", "B", "C", "LOI"], nguong_loi=0.3, fetch_fn=fetch_gia)
    assert set(kq.keys()) == {"A", "B", "C"}


def test_fetch_lnst_batch_tren_nguong_nem_loi():
    def fetch_gia_loi_het(symbol):
        return None

    with pytest.raises(RuntimeError, match="lỗi"):
        md.fetch_lnst_batch(["A", "B", "C", "D"], nguong_loi=0.3, fetch_fn=fetch_gia_loi_het)


def test_fetch_lnst_batch_nguong_mac_dinh_cao_hon_fetch_daily_batch():
    """LNST vien duoc it ma nho HOSE khong co BCTC day du, nen nguong loi phai cao hon 0.3 mac dinh cua gia."""
    import inspect
    sig = inspect.signature(md.fetch_lnst_batch)
    assert sig.parameters["nguong_loi"].default == 0.5


# ---------------------------------------------------------------------------
# cached(): cua so gia QUA KHU da chot phai dung cache BAT BIEN (khong gan
# ngay, khong bao gio het han) - nguyen nhan #1 gay tai lai toan bo vu tru moi
# ngay du du lieu qua khu khong doi.
# ---------------------------------------------------------------------------

def test_fetch_daily_cua_so_qua_khu_dung_cache_bat_bien_khong_gan_ngay(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 9), fromisoformat=date.fromisoformat))
    dem = {"n": 0}
    raw = pd.DataFrame({"time": ["2026-01-05"], "close": [10.0], "volume": [100]})

    class FakeQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval):
            dem["n"] += 1
            return raw

    fake_vnstock = SimpleNamespace(Quote=FakeQuote)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    # end = 2026-01-10 < hom nay (2026-09-09) -> qua khu da chot -> cache bat bien
    fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    file_bat_bien = tmp_path / "lichsu" / "daily-VIC-2026-01-01-2026-01-10.json"
    assert file_bat_bien.exists()
    assert not list(tmp_path.glob("daily-VIC-2026-01-01-2026-01-10-*.json"))

    # Doi "hom nay" sang ngay khac (nhu se xay ra khi chay lai vao hom sau) -
    # cache bat bien KHONG duoc goi lai mang.
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 10), fromisoformat=date.fromisoformat))
    fetch_daily("VIC", date(2026, 1, 1), date(2026, 1, 10))
    assert dem["n"] == 1, "Cache bat bien khong duoc het han khi doi ngay he thong"


def test_fetch_daily_cua_so_dang_song_van_cache_theo_ngay(tmp_path, monkeypatch):
    """end = hom nay -> cua so con co the phat sinh phien moi -> giu cache theo ngay cu."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 9), fromisoformat=date.fromisoformat))
    raw = pd.DataFrame({"time": ["2026-09-09"], "close": [10.0], "volume": [100]})

    class FakeQuote:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval):
            return raw

    fake_vnstock = SimpleNamespace(Quote=FakeQuote)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    fetch_daily("VIC", date(2026, 9, 1), date(2026, 9, 9))
    assert (tmp_path / "daily-VIC-2026-09-01-2026-09-09-2026-09-09.json").exists()
    assert not (tmp_path / "lichsu").exists()


# ---------------------------------------------------------------------------
# Sua loi: KHONG duoc cache ket qua RONG - mot lan fn() that bai (mang loi,
# rate-limit...) khong duoc bien thanh "vinh vien khong co du lieu". Xem
# canh_bao trong report task-cache-rong.
# ---------------------------------------------------------------------------

def test_cached_khong_ghi_file_khi_ket_qua_rong_theo_dang_cache(tmp_path):
    """Khi truyen dang_cache va fn() tra ve gia tri khong dang cache, cached()
    phai TRA VE ket qua do cho nguoi goi nhung KHONG ghi file xuong dia."""
    dem = {"n": 0}

    def that():
        dem["n"] += 1
        return {"records": []}

    kq1 = cached(that, "thu-rong", tmp_path, dang_cache=lambda kq: len(kq.get("records", [])) > 0)
    assert kq1 == {"records": []}
    assert not list(tmp_path.glob("*.json")), "Ket qua rong khong duoc ghi file cache"

    # Lan goi thu hai phai goi lai fn(), khong duoc lay tu cache (vi khong co file)
    cached(that, "thu-rong", tmp_path, dang_cache=lambda kq: len(kq.get("records", [])) > 0)
    assert dem["n"] == 2, "Ket qua rong khong duoc cache -> lan sau phai goi lai fn()"


def test_cached_van_ghi_file_khi_ket_qua_khong_rong_theo_dang_cache(tmp_path):
    """dang_cache tra True thi hanh vi cache binh thuong nhu cu."""
    dem = {"n": 0}

    def that():
        dem["n"] += 1
        return {"records": [{"time": "2026-01-05", "close": 10.0, "volume": 100}]}

    cached(that, "thu-day", tmp_path, dang_cache=lambda kq: len(kq.get("records", [])) > 0)
    cached(that, "thu-day", tmp_path, dang_cache=lambda kq: len(kq.get("records", [])) > 0)
    assert dem["n"] == 1, "Ket qua khong rong van phai cache binh thuong"
    assert list(tmp_path.glob("*.json"))


def test_cached_mac_dinh_dang_cache_none_van_cache_moi_thu_nhu_cu(tmp_path):
    """Khong truyen dang_cache (None) -> hanh vi cu: cache moi ket qua, ke ca rong.
    Bao dam khong pha vo cac ham fetch khac dang goi cached() ma khong truyen tham so nay."""
    dem = {"n": 0}

    def that():
        dem["n"] += 1
        return {"records": []}

    cached(that, "thu-mac-dinh", tmp_path)
    cached(that, "thu-mac-dinh", tmp_path)
    assert dem["n"] == 1, "Khong truyen dang_cache thi van cache moi thu nhu truoc gio"


def test_fetch_daily_khong_cache_khi_goi_that_tra_ve_rong(tmp_path, monkeypatch):
    """Day chinh la loi that: fetch_daily voi ma dang niem yet nhung goi mang
    that bai (vi du timeout) tra ve DataFrame rong -> KHONG duoc cache vinh vien
    thanh "khong co du lieu". Lan goi sau (co the mang da on dinh lai) phai
    duoc thu lai, khong duoc doc lai file cache rong cu."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 9), fromisoformat=date.fromisoformat))
    dem = {"n": 0}

    class FakeQuoteLoi:
        def __init__(self, symbol, source):
            pass

        def history(self, start, end, interval):
            dem["n"] += 1
            raise RuntimeError("Gia lap loi mang / rate-limit")

    fake_vnstock = SimpleNamespace(Quote=FakeQuoteLoi)
    monkeypatch.setitem(__import__("sys").modules, "vnstock", fake_vnstock)

    df1 = fetch_daily("DGC", date(2025, 7, 8), date(2026, 7, 15))
    assert df1.empty

    file_bat_bien = tmp_path / "lichsu" / "daily-DGC-2025-07-08-2026-07-15.json"
    assert not file_bat_bien.exists(), "Ket qua rong do loi mang khong duoc cache vinh vien"

    df2 = fetch_daily("DGC", date(2025, 7, 8), date(2026, 7, 15))
    assert df2.empty
    assert dem["n"] == 2, "Lan goi sau phai thu lai mang, khong duoc doc cache rong cu"


def test_fetch_lnst_boc_duoc_chi_tieu_cua_bo_bao_cao_bao_hiem(tmp_path, monkeypatch):
    """BCTC bao hiem (vd BVH) KHONG co dong attributable_to_parent_company; chi tieu
    tuong duong ten la net_profit_attributable_to_shareholders_of_the_group.
    Truoc khi sua, BVH tra None va bi gan nhan "thieu du lieu" oan."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    df_quy = _df_bctc(
        ["profit_after_tax", "minority_interest",
         "net_profit_attributable_to_shareholders_of_the_group"],
        **{"2026-Q2": [1047, 15, 1032], "2026-Q1": [816, 16, 799]},
    )

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            return df_quy

    monkeypatch.setitem(__import__("sys").modules, "vnstock",
                        SimpleNamespace(Finance=FakeFinance))

    kq = md.fetch_lnst("BVH")
    assert kq is not None
    assert kq["lnst_vnd"] == 1032 + 799
    assert "net_profit_attributable_to_shareholders_of_the_group" in kq["nguon"]


def test_fetch_lnst_uu_tien_chi_tieu_cong_ty_me_khi_co_ca_hai(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    df_quy = _df_bctc(
        ["attributable_to_parent_company",
         "net_profit_attributable_to_shareholders_of_the_group"],
        **{"2026-Q2": [10, 999], "2026-Q1": [5, 999]},
    )

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            return df_quy

    monkeypatch.setitem(__import__("sys").modules, "vnstock",
                        SimpleNamespace(Finance=FakeFinance))

    assert md.fetch_lnst("FPT")["lnst_vnd"] == 15


def test_fetch_lnst_khong_cache_ket_qua_none(tmp_path, monkeypatch):
    """None gan nhu luon la LOI LAY DU LIEU (mang/rate-limit/schema la), khong phai
    su that "doanh nghiep khong co LNST" - cache lai se khoa cai loi do suot ca ngay."""
    monkeypatch.setattr(md, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(md, "date", SimpleNamespace(today=lambda: date(2026, 9, 8)))

    class FakeFinance:
        def __init__(self, symbol, source):
            pass

        def income_statement(self, period, lang):
            raise RuntimeError("API sập")

    monkeypatch.setitem(__import__("sys").modules, "vnstock",
                        SimpleNamespace(Finance=FakeFinance))

    assert md.fetch_lnst("XYZ") is None
    assert list(tmp_path.glob("lnst-XYZ-*.json")) == []
