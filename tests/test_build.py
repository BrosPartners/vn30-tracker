from datetime import date

import pandas as pd

from build import lap_stock_inputs, xuat_json
from rules.basket import build_vn30

TIMES = pd.to_datetime(["2026-01-05", "2026-02-05"])


def _daily(close=50.0, volume=1_000_000):
    return pd.DataFrame({"time": TIMES, "close": [close] * 2, "volume": [volume] * 2})


def test_ghep_du_lieu_nhap_tay_vao_stock_input():
    manual = {"VIC": {"free_float": 0.30, "free_float_source": "x",
                      "listing_date": date(2018, 5, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000},
                          manual, previous_basket=["VIC"])
    assert ds[0].free_float == 0.30
    assert ds[0].in_previous_basket is True
    assert ds[0].shares_outstanding == 7_762_186_000


def test_ma_khong_co_trong_manual_van_duoc_giu_voi_free_float_none():
    """Van phai tinh GTVH de xep hang, chi la khong ket luan duoc."""
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [])
    assert len(ds) == 1
    assert ds[0].free_float is None


def test_ma_thieu_slcp_bi_bo_qua():
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {}, {}, [])
    assert ds == []


def test_json_co_du_cac_khoi_web_can():
    manual = {"VIC": {"free_float": 0.30, "free_float_source": "x",
                      "listing_date": date(2018, 5, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, manual, ["VIC"])
    kq = xuat_json(build_vn30(ds, date(2026, 7, 1)), date(2026, 7, 1), "07/2026")

    assert set(kq) >= {"as_of", "ky_review", "constituents", "reserve",
                       "stocks", "missing_data", "xap_xi"}
    dong = kq["stocks"][0]
    assert set(dong) >= {"symbol", "gtvh_rank", "gtvh_ty", "gtgd_kl_ty", "klgd_kl",
                         "turnover", "free_float", "ket_luan", "canh_bao", "screens"}
    assert dong["canh_bao"] == [], "VIC khai bao unqualified nên không có cảnh báo"
    assert dong["gtvh_ty"] == round(dong["gtvh_ty"], 1)


def test_json_ghi_ro_ba_xap_xi():
    """Web phai luon hien canh bao ve gioi han du lieu - khong duoc am tham bo."""
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [])
    kq = xuat_json(build_vn30(ds, date(2026, 7, 1)), date(2026, 7, 1), "07/2026")
    assert len(kq["xap_xi"]) == 3
    assert any("thỏa thuận" in x for x in kq["xap_xi"])


def test_json_co_khoi_canh_bao_chung_tu_basket_result():
    """canh_bao cua BasketResult (vd ro chon duoc < 30 ma) phai duoc dua ra JSON."""
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [])
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    assert kq["canh_bao"] == r.canh_bao
