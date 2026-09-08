from datetime import date

import pandas as pd
import pytest

from collectors.market_data import chuan_hoa_daily, cached


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
