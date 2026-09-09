from datetime import date

import pandas as pd

from build import (
    MANUAL_FILE,
    canh_bao_ma_ro_cu_bien_mat,
    lap_stock_inputs,
    load_free_float_moi_nhat,
    xuat_json,
)
from collectors.manual_data import load_manual
from rules.basket import build_vn30
from rules.models import StockInput

TIMES = pd.to_datetime(["2026-01-05", "2026-02-05"])


def _daily(close=50.0, volume=1_000_000):
    return pd.DataFrame({"time": TIMES, "close": [close] * 2, "volume": [volume] * 2})


def test_ghep_du_lieu_nhap_tay_vao_stock_input():
    manual = {"VIC": {"listing_date": date(2018, 5, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {"VIC": 0.30}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000},
                          manual, previous_basket=["VIC"], free_float=free_float)
    assert ds[0].free_float == 0.30
    assert ds[0].in_previous_basket is True
    assert ds[0].shares_outstanding == 7_762_186_000


def test_ma_khong_co_trong_manual_van_duoc_giu_voi_free_float_none():
    """Van phai tinh GTVH de xep hang, chi la khong ket luan duoc."""
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {})
    assert len(ds) == 1
    assert ds[0].free_float is None


def test_ma_khong_co_trong_cong_bo_hose_thi_free_float_none_khong_doan():
    """Ma khong co trong cong bo chinh thuc HOSE (vd MCH, TCX) phai la None, tuyet doi khong doan."""
    free_float = {"VIC": 0.30}  # khong co MCH
    ds = lap_stock_inputs(["MCH"], {"MCH": _daily()}, {"MCH": 1_000_000}, {}, [], free_float)
    assert ds[0].free_float is None


def test_ma_khong_co_trong_manual_thi_listing_date_la_none_khong_phai_nam_1900():
    """Bug da fix: truoc day mac dinh date(1900,1,1) -> bia ra 'Da niem yet 1500+ thang'."""
    ds = lap_stock_inputs(["BID"], {"BID": _daily()}, {"BID": 1_000_000}, {}, [], {})
    assert ds[0].listing_date is None


def test_ma_thieu_listing_date_nam_trong_missing_data_va_ket_luan_thieu_du_lieu():
    manual = {"BID": {"warning_status": "none", "lnst_positive": True,
                      "audit_opinion": "unqualified"}}  # KHONG co listing_date
    free_float = {"BID": 0.30}
    ds = lap_stock_inputs(["BID"], {"BID": _daily()}, {"BID": 1_000_000}, manual, [], free_float)
    r = build_vn30(ds, date(2026, 7, 1))
    assert "BID" in r.missing_data
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "BID")
    assert dong["ket_luan"] == "Thiếu dữ liệu"


def test_khong_co_ma_nao_bia_thong_bao_niem_yet_so_thang_lon_vo_ly():
    """Bao ve toan he thong: khong duoc co thong bao kieu 'Da niem yet 1520 thang'."""
    manual = {"BID": {"warning_status": "none", "lnst_positive": True,
                      "audit_opinion": "unqualified"}}
    free_float = {"BID": 0.30}
    ds = lap_stock_inputs(["BID"], {"BID": _daily()}, {"BID": 1_000_000}, manual, [], free_float)
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    for dong in kq["stocks"]:
        for sc in dong["screens"]:
            assert "1500" not in sc["message"] and "1520" not in sc["message"]


def test_ma_thieu_slcp_bi_bo_qua():
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {}, {}, [], {})
    assert ds == []


def test_json_co_du_cac_khoi_web_can():
    manual = {"VIC": {"listing_date": date(2018, 5, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {"VIC": 0.30}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, manual, ["VIC"], free_float)
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
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {})
    kq = xuat_json(build_vn30(ds, date(2026, 7, 1)), date(2026, 7, 1), "07/2026")
    assert len(kq["xap_xi"]) == 6
    assert any("thỏa thuận" in x for x in kq["xap_xi"])
    assert any("consideration_list_size" in x for x in kq["xap_xi"])


def test_json_co_khoi_canh_bao_chung_tu_basket_result():
    """canh_bao cua BasketResult (vd ro chon duoc < 30 ma) phai duoc dua ra JSON."""
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {})
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    assert kq["canh_bao"] == r.canh_bao


def test_load_free_float_moi_nhat_lay_ky_moi_nhat(tmp_path):
    """Neu co nhieu file <ky>.yaml, phai lay dung ky moi nhat (so sanh chuoi YYYY-MM)."""
    import yaml
    (tmp_path / "2026-01.yaml").write_text(
        yaml.safe_dump({"ky": "2026-01", "free_float": {"ACB": 0.85}}, allow_unicode=True),
        encoding="utf-8")
    (tmp_path / "2025-10.yaml").write_text(
        yaml.safe_dump({"ky": "2025-10", "free_float": {"ACB": 0.5}}, allow_unicode=True),
        encoding="utf-8")
    ff, ky = load_free_float_moi_nhat(tmp_path)
    assert ky == "2026-01"
    assert ff["ACB"] == 0.85


def test_load_free_float_moi_nhat_khong_co_file_tra_ve_rong(tmp_path):
    ff, ky = load_free_float_moi_nhat(tmp_path)
    assert ff == {}
    assert ky is None


# ---------------------------------------------------------------------------
# LNST tu dong + lop ghi de manual.yaml
# ---------------------------------------------------------------------------

def test_lnst_tu_dong_duoc_dung_khi_khong_co_trong_manual():
    lnst_auto = {"FPT": {"lnst_vnd": 9_376_127_629_501, "ky": "Năm 2025", "nguon": "vnstock BCTC năm"}}
    ds = lap_stock_inputs(["FPT"], {"FPT": _daily()}, {"FPT": 1_000_000}, {}, [], {}, lnst_auto)
    assert ds[0].lnst_positive is True
    assert ds[0].lnst_ty == round(9_376_127_629_501 / 1e9, 1)
    assert ds[0].lnst_ky == "Năm 2025"
    assert ds[0].lnst_nguon == "tự động"


def test_lnst_am_tu_dong_ra_lnst_positive_false():
    lnst_auto = {"ABC": {"lnst_vnd": -1_000_000_000, "ky": "Năm 2025", "nguon": "x"}}
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {}, lnst_auto)
    assert ds[0].lnst_positive is False


def test_manual_ghi_de_thang_so_tu_dong():
    """Neu manual.yaml co khai bao lnst_positive cho ma, gia tri do THANG so tu dong."""
    manual = {"FPT": {"warning_status": "none", "lnst_positive": False, "audit_opinion": "unknown"}}
    lnst_auto = {"FPT": {"lnst_vnd": 9_376_127_629_501, "ky": "Năm 2025", "nguon": "vnstock BCTC năm"}}
    ds = lap_stock_inputs(["FPT"], {"FPT": _daily()}, {"FPT": 1_000_000}, manual, [], {}, lnst_auto)
    assert ds[0].lnst_positive is False, "manual.yaml phai thang so tu dong (nguoi xac nhan cao hon may)"
    assert ds[0].lnst_nguon == "xác nhận thủ công"


def test_ma_khong_co_ca_manual_lan_tu_dong_thi_lnst_positive_none():
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {}, {})
    assert ds[0].lnst_positive is None
    assert ds[0].lnst_ty is None
    assert ds[0].lnst_nguon is None


def test_json_co_lnst_ty_ky_nguon_va_lay_dung_gia_tri_tu_dong():
    lnst_auto = {"VIC": {"lnst_vnd": 9_376_127_629_501, "ky": "Năm 2025", "nguon": "vnstock BCTC năm"}}
    manual = {"VIC": {"listing_date": date(2018, 5, 1), "warning_status": "none"}}
    free_float = {"VIC": 0.30}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, manual, ["VIC"],
                          free_float, lnst_auto)
    kq = xuat_json(build_vn30(ds, date(2026, 7, 1)), date(2026, 7, 1), "07/2026")
    dong = kq["stocks"][0]
    assert dong["lnst_ty"] == round(9_376_127_629_501 / 1e9, 1)
    assert dong["lnst_ky"] == "Năm 2025"
    assert dong["lnst_nguon"] == "tự động"


def test_json_lnst_nguon_xac_nhan_thu_cong_khi_manual_ghi_de():
    manual = {"VIC": {"listing_date": date(2018, 5, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {"VIC": 0.30}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, manual, ["VIC"], free_float, {})
    kq = xuat_json(build_vn30(ds, date(2026, 7, 1)), date(2026, 7, 1), "07/2026")
    dong = kq["stocks"][0]
    assert dong["lnst_nguon"] == "xác nhận thủ công"


def test_ma_khong_co_lnst_nam_trong_missing_data_va_ket_luan_thieu_du_lieu():
    manual = {"BID": {"listing_date": date(2016, 1, 1), "warning_status": "none"}}
    free_float = {"BID": 0.30}
    ds = lap_stock_inputs(["BID"], {"BID": _daily()}, {"BID": 1_000_000}, manual, [], free_float, {})
    r = build_vn30(ds, date(2026, 7, 1))
    assert "BID" in r.missing_data
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "BID")
    assert dong["ket_luan"] == "Thiếu dữ liệu"


# ---------------------------------------------------------------------------
# Suy ngay niem yet tu chuoi gia (khong co listing_date xac nhan trong manual.yaml)
# ---------------------------------------------------------------------------

def _daily_tu(ngay_dau: str, so_phien: int = 2):
    times = pd.date_range(ngay_dau, periods=so_phien, freq="D")
    return pd.DataFrame({"time": times, "close": [50.0] * so_phien, "volume": [1_000_000] * so_phien})


def test_chuoi_gia_bat_dau_sat_dau_cua_so_thi_suy_ra_niem_yet_truoc_cua_so():
    """Ngay giao dich dau tien chi sau ngay bat dau cua so 1 ngay (trong dung sai 5 ngay
    lam viec) -> coi la da giao dich tu truoc cua so, KHONG duoc bia ngay niem yet cu the."""
    start = date(2025, 7, 1)
    free_float = {"ABC": 0.30}
    lnst_auto = {"ABC": {"lnst_vnd": 1_000_000_000, "ky": "Năm 2025", "nguon": "x"}}
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily_tu("2025-07-02")}, {"ABC": 1_000_000},
                          {}, [], free_float, lnst_auto, start=start)
    assert ds[0].listing_date is None, "khong duoc bia ngay niem yet cu the"
    assert ds[0].niem_yet_truoc_cua_so is True
    assert ds[0].niem_yet_nguon == "giao dịch từ trước cửa sổ dữ liệu"

    r = build_vn30(ds, date(2026, 7, 1))
    assert "ABC" not in r.missing_data, "niem_yet_truoc_cua_so la bang chung hop le, khong phai thieu du lieu"
    assert r.screens["ABC"][0].passed
    assert "trước cửa sổ dữ liệu" in r.screens["ABC"][0].message


def test_chuoi_gia_bat_dau_muon_hon_nhieu_thi_suy_ra_ngay_niem_yet_va_truot_6_thang():
    """Ma len san 2 thang truoc ngay chot -> suy ra listing_date, screen_eligibility
    phai TRUOT vi chua du 6 thang, va shortfall dung so thang con thieu."""
    as_of = date(2026, 7, 1)
    start = date(2025, 7, 1)
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily_tu("2026-05-01")}, {"ABC": 1_000_000},
                          {}, [], {}, start=start)
    assert ds[0].listing_date == date(2026, 5, 1)
    assert ds[0].niem_yet_truoc_cua_so is False
    assert ds[0].niem_yet_nguon == "suy từ ngày giao dịch đầu tiên"

    r = build_vn30(ds, as_of)
    eligibility = r.screens["ABC"][0]
    assert not eligibility.passed
    assert eligibility.shortfall == 4


def test_chuoi_gia_bat_dau_8_thang_truoc_thi_dat():
    """Ma len san 8 thang truoc ngay chot -> suy ra listing_date, du 6 thang nen dat."""
    as_of = date(2026, 7, 1)
    start = date(2025, 7, 1)
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily_tu("2025-11-01")}, {"ABC": 1_000_000},
                          {}, [], {}, start=start)
    assert ds[0].listing_date == date(2025, 11, 1)

    r = build_vn30(ds, as_of)
    eligibility = r.screens["ABC"][0]
    assert eligibility.passed
    assert "8 tháng" in eligibility.message


def test_manual_listing_date_thang_so_suy_ra():
    """manual.yaml co listing_date thi PHAI thang so suy tu chuoi gia."""
    manual = {"VIC": {"listing_date": date(2018, 5, 1), "warning_status": "none"}}
    start = date(2025, 7, 1)
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily_tu("2026-05-01")}, {"VIC": 1_000_000},
                          manual, [], {}, start=start)
    assert ds[0].listing_date == date(2018, 5, 1)
    assert ds[0].niem_yet_truoc_cua_so is False
    assert ds[0].niem_yet_nguon == "xác nhận thủ công"


def test_khong_truyen_start_thi_giu_hanh_vi_cu_khong_suy_doan():
    """Neu khong truyen start (goi cu, vd test cu), khong duoc tu y suy doan - giu
    hanh vi cu: khong co manual thi listing_date la None."""
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {})
    assert ds[0].listing_date is None
    assert ds[0].niem_yet_truoc_cua_so is False


def test_ma_khong_co_du_lieu_gia_van_bi_loc_khoi_vu_tru():
    """Hanh vi cu khong doi: ma khong co gia (df rong) bi bo qua hoan toan, du co start."""
    import pandas as pd
    rong = pd.DataFrame(columns=["time", "close", "volume"])
    ds = lap_stock_inputs(["ABC"], {"ABC": rong}, {"ABC": 1_000_000}, {}, [], {},
                          start=date(2025, 7, 1))
    assert ds == []


# ---------------------------------------------------------------------------
# Gom lich su snapshot cho sparkline (Task 9.5)
# ---------------------------------------------------------------------------

def test_gom_lich_su_theo_ma(tmp_path):
    import json

    from build import gom_lich_su

    h = tmp_path / "history"
    h.mkdir()
    for ngay, hang in [("2026-09-01", 31), ("2026-09-02", 29)]:
        (h / f"{ngay}.json").write_text(json.dumps({
            "as_of": ngay,
            "stocks": [{"symbol": "VIX", "gtvh_rank": hang, "gtgd_kl_ty": 100.0}],
        }), encoding="utf-8")

    ls = gom_lich_su(h)
    assert [d["gtvh_rank"] for d in ls["VIX"]] == [31, 29], "Phải sắp theo ngày tăng dần"


def test_gom_lich_su_thu_muc_khong_ton_tai_tra_ve_rong(tmp_path):
    from build import gom_lich_su
    assert gom_lich_su(tmp_path / "khong_ton_tai") == {}


# ---------------------------------------------------------------------------
# Tuyen phong thu thu hai: ma ro cu bien mat khoi vu tru (khong lay duoc du
# lieu gia) phai duoc canh bao to, khong am tham lot qua (xem sua loi cache rong).
# ---------------------------------------------------------------------------

def test_canh_bao_ma_ro_cu_bien_mat_khi_khong_con_trong_vu_tru():
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, {}, [], {})
    canh_bao = canh_bao_ma_ro_cu_bien_mat(["VIC", "DGC"], ds)
    assert len(canh_bao) == 1
    assert "DGC" in canh_bao[0]
    assert "VIC" not in canh_bao[0]


def test_khong_canh_bao_khi_tat_ca_ma_ro_cu_van_con_trong_vu_tru():
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, {}, [], {})
    assert canh_bao_ma_ro_cu_bien_mat(["VIC"], ds) == []


def test_canh_bao_ma_ro_cu_bien_mat_khong_phan_biet_hoa_thuong():
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, {}, [], {})
    assert canh_bao_ma_ro_cu_bien_mat(["vic"], ds) == []


def test_canh_bao_ma_ro_cu_bien_mat_neu_dich_danh_nhieu_ma():
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily()}, {"VIC": 7_762_186_000}, {}, [], {})
    canh_bao = canh_bao_ma_ro_cu_bien_mat(["VIC", "DGC", "BSR"], ds)
    assert len(canh_bao) == 2
    ma_neu = " ".join(canh_bao)
    assert "DGC" in ma_neu and "BSR" in ma_neu


# ---------------------------------------------------------------------------
# Canh bao chuyen san (vd MCH: HOSE cong bo lich su UPCoM lan HOSE nen ngay giao
# dich dau tien trong chuoi gia KHONG phai ngay niem yet HOSE). Tuyen kiem tra
# cheo: mac dinh "niem_yet_truoc_cua_so" doi voi danh muc VNAllshare cong bo
# chinh thuc cua HOSE (free_float dict tu data/hose_index/<ky>.yaml, key la
# chinh tap ma VNAllshare da qua sang loc - xem scripts/cap_nhat_cbtt.py).
# ---------------------------------------------------------------------------

def test_ma_suy_truoc_cua_so_nhung_khong_co_trong_vnallshare_thi_canh_bao():
    """Ma dat dieu kien tham gia CHI nho suy luan 'giao dich tu truoc cua so',
    khong co xac nhan thu cong, va KHONG co trong cong bo VNAllshare gan nhat
    (free_float dict) -> nghi ngo moi chuyen san, phai gan canh bao."""
    start = date(2025, 7, 1)
    free_float = {"VIC": 0.30}  # khong co MCH trong cong bo VNAllshare ky nay
    ds = lap_stock_inputs(["MCH"], {"MCH": _daily_tu("2025-07-02")}, {"MCH": 1_000_000},
                          {}, [], free_float, start=start)
    assert ds[0].niem_yet_truoc_cua_so is True
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "MCH")
    assert any("chuyển sàn" in cb or "VNAllshare" in cb for cb in dong["canh_bao"])


def test_ma_suy_truoc_cua_so_va_co_trong_vnallshare_thi_khong_canh_bao():
    """Cung suy luan 'truoc cua so' nhung ma CO mat trong cong bo VNAllshare
    gan nhat -> khong co dau hieu chuyen san, khong canh bao."""
    start = date(2025, 7, 1)
    free_float = {"ABC": 0.30}  # ABC CO trong cong bo VNAllshare ky nay
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily_tu("2025-07-02")}, {"ABC": 1_000_000},
                          {}, [], free_float, start=start)
    assert ds[0].niem_yet_truoc_cua_so is True
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "ABC")
    assert not any("chuyển sàn" in cb or "VNAllshare" in cb for cb in dong["canh_bao"])


def test_ma_co_listing_date_xac_nhan_thu_cong_thi_khong_canh_bao_chuyen_san():
    """Nguoi da xac nhan listing_date thu cong thi tin nguoi, du ma khong co
    trong cong bo VNAllshare ky nay (co the cong bo cu hon thuc te)."""
    manual = {"MCH": {"listing_date": date(2025, 12, 1), "warning_status": "none"}}
    free_float = {}  # khong co MCH trong cong bo VNAllshare ky nay
    ds = lap_stock_inputs(["MCH"], {"MCH": _daily_tu("2023-10-31")}, {"MCH": 1_000_000},
                          manual, [], free_float)
    assert ds[0].niem_yet_nguon == "xác nhận thủ công"
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "MCH")
    assert not any("chuyển sàn" in cb or "VNAllshare" in cb for cb in dong["canh_bao"])


def test_mch_sau_khi_ghi_de_manual_thi_niem_yet_tu_thang_12_2025():
    """MCH: chao san HOSE that 25/12/2025 nhung chuoi gia (UPCoM+HOSE gop) bat dau
    tu 31/10/2023 -> khong co listing_date thu cong se suy sai. Sau khi ghi de
    trong data/manual.yaml, niem_yet_nguon phai la 'xác nhận thủ công' va so
    thang tinh tu 2025-12."""
    manual = load_manual(MANUAL_FILE)
    assert "MCH" in manual, "data/manual.yaml phai co ghi de MCH (xem task chuyen san)"
    assert manual["MCH"]["listing_date"] == date(2025, 12, 1)
    free_float = {}
    ds = lap_stock_inputs(["MCH"], {"MCH": _daily_tu("2023-10-31")}, {"MCH": 1_000_000},
                          manual, [], free_float)
    assert ds[0].niem_yet_nguon == "xác nhận thủ công"
    r = build_vn30(ds, date(2026, 7, 1))
    assert r.metrics["MCH"]["niem_yet_thang"] == 7  # 2025-12 -> 2026-07 = 7 thang


def test_json_xuat_thieu_du_lieu_cho_moi_buoc_sang_loc():
    """Web dung truong nay o tang du lieu de tach nhom 'nguy co bi loai' khoi
    'chua ket luan duoc' - khong duoc do chuoi tieng Viet (de vo)."""
    manual = {"BID": {"warning_status": "none", "lnst_positive": True,
                      "audit_opinion": "unqualified"}}  # KHONG co listing_date
    free_float = {"BID": 0.30}
    ds = lap_stock_inputs(["BID"], {"BID": _daily()}, {"BID": 1_000_000}, manual, [], free_float)
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "BID")
    truot = [sc for sc in dong["screens"] if not sc["passed"]]
    assert truot, "BID phai truot it nhat 1 buoc (thieu ngay niem yet)"
    assert all("thieu_du_lieu" in sc for sc in dong["screens"])
    # BID chi truot vi thieu ngay niem yet -> moi buoc truot deu thieu_du_lieu=True,
    # nghia la day la ma "chua ket luan duoc", KHONG phai "nguy co bi loai" that su.
    assert all(sc["thieu_du_lieu"] for sc in truot)


def test_ma_trong_ro_ky_truoc_chi_truot_vi_thieu_du_lieu_khong_phai_nguy_co_that():
    """Mo phong tinh huong MCH/TCX: ma trong ro ky truoc, von hoa cao, nhung
    thieu free float (chua co trong cong bo HOSE) -> phai truot free_float VOI
    thieu_du_lieu=True, khong co buoc nao truot vi ly do thuc chat. Day la can cu
    de tang web KHONG duoc xep ma nay vao nhom 'nguy co bi loai'."""
    manual = {"MCH": {"listing_date": date(2015, 1, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {}  # MCH khong co trong cong bo HOSE ky nay
    ds = lap_stock_inputs(["MCH"], {"MCH": _daily(volume=2_000_000)}, {"MCH": 1_000_000},
                          manual, previous_basket=["MCH"], free_float=free_float)
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "MCH")
    truot = [sc for sc in dong["screens"] if not sc["passed"]]
    assert truot
    assert all(sc["thieu_du_lieu"] for sc in truot), \
        "MCH chi truot vi thieu free float, khong phai truot thuc chat"


# ---------------------------------------------------------------------------
# Phan biet (a) "HOSE da xet va loai khoi VNAllshare" voi (b) "thieu du lieu thuc
# su" khi mot ma HOSE khong co trong cong bo VNAllshare gan nhat (xem task: mã
# HVN, hạng vốn hóa 26, vắng mặt ở cả 2 kỳ công bố vì bị chuyển sang diện cảnh báo).
# ---------------------------------------------------------------------------

def test_ma_giao_dich_tu_lau_vang_mat_vnallshare_thi_hose_loai_khong_phai_thieu_du_lieu():
    """Ma da giao dich tren HOSE tu TRUOC ngay chot cua ky cong bo (xac nhan thu
    cong listing_date), nhung khong co trong VNAllshare -> HOSE DA XET va LOAI,
    KHONG duoc coi la thieu du lieu."""
    manual = {"HVN": {"listing_date": date(2020, 1, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {}  # HVN khong co trong cong bo VNAllshare ky nay
    ds = lap_stock_inputs(["HVN"], {"HVN": _daily(volume=2_000_000)}, {"HVN": 1_000_000},
                          manual, previous_basket=[], free_float=free_float, ky_cbtt="2026-07")
    assert ds[0].hose_loai_khoi_vnallshare is True
    r = build_vn30(ds, date(2026, 7, 1))
    assert "HVN" not in r.missing_data
    assert not any("HVN" in cb and "thiếu dữ liệu" in cb.lower() for cb in r.canh_bao), \
        "khong duoc kich hoat canh bao 'thieu du lieu' cho HVN vi day khong con la thieu du lieu"
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "HVN")
    assert dong["ket_luan"] == "HOSE loại khỏi VNAllshare"
    buoc_ff = next(sc for sc in dong["screens"] if sc["step"] == "free_float")
    assert not buoc_ff["passed"]
    assert buoc_ff["thieu_du_lieu"] is False
    assert "07/2026" in buoc_ff["message"]


def test_ma_moi_giao_dich_sau_ngay_chot_vang_mat_vnallshare_van_la_thieu_du_lieu():
    """Ma moi bat dau giao dich SAU ngay chot cua ky cong bo (vd niem yet 2026-08,
    sau ngay chot 2026-07-15) -> HOSE CHUA TUNG XET, day moi thuc su la thieu du
    lieu, VA phai kich hoat canh bao do neu hang von hoa du dieu kien."""
    manual = {"MOI": {"listing_date": date(2026, 8, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {}
    ds = lap_stock_inputs(["MOI"], {"MOI": _daily(volume=2_000_000)}, {"MOI": 1_000_000},
                          manual, previous_basket=[], free_float=free_float, ky_cbtt="2026-07")
    assert ds[0].hose_loai_khoi_vnallshare is False
    r = build_vn30(ds, date(2026, 7, 1))
    assert "MOI" in r.missing_data
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "MOI")
    # Nhan hien thi la "Không đạt" chu khong phai "Thiếu dữ liệu": ma nay con truot
    # Dieu 3.2 mot cach dut khoat (chua niem yet du 6 thang), va ly do dut khoat
    # thang nhan thieu du lieu - xem build._ket_luan. Diem cua test nay la ngu nghia
    # cua BUOC free_float ben duoi, khong phai nhan tong hop.
    assert dong["ket_luan"] == "Không đạt"
    buoc_ff = next(sc for sc in dong["screens"] if sc["step"] == "free_float")
    assert buoc_ff["thieu_du_lieu"] is True


def test_ma_co_trong_vnallshare_hanh_vi_khong_doi_du_co_ky_cbtt():
    """Truyen them ky_cbtt khong duoc lam thay doi hanh vi cua ma DA CO trong
    cong bo VNAllshare (co free_float)."""
    manual = {"VIC": {"listing_date": date(2018, 5, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    free_float = {"VIC": 0.30}
    ds = lap_stock_inputs(["VIC"], {"VIC": _daily(volume=2_000_000)}, {"VIC": 7_762_186_000},
                          manual, previous_basket=["VIC"], free_float=free_float, ky_cbtt="2026-07")
    assert ds[0].hose_loai_khoi_vnallshare is False
    r = build_vn30(ds, date(2026, 7, 1))
    assert "VIC" not in r.missing_data


def test_hvn_co_trong_manual_voi_warning_status():
    """HVN phai duoc ghi thu cong trong data/manual.yaml voi warning_status=warning
    (xem task hose-loai 2026-09-09: HOSE chuyen HVN sang dien canh bao tu 14/07/2026)."""
    manual = load_manual(MANUAL_FILE)
    assert "HVN" in manual, "data/manual.yaml phai co ghi de HVN (dien canh bao)"
    assert manual["HVN"]["warning_status"] == "warning"


def test_canh_bao_bien_mat_khi_ma_hang_cao_la_hose_loai_khong_phai_thieu_du_lieu():
    """Tai hien dung tinh huong HVN trong task: ma hang von hoa <= 40 vang mat
    VNAllshare vi HOSE da loai -> KHONG duoc kich hoat canh bao do dau trang."""
    def make(symbol, close, free_float=None, listing=date(2015, 1, 1)):
        return StockInput(
            symbol=symbol,
            daily=pd.DataFrame({"time": TIMES, "close": [close, close],
                                "volume": [2_000_000, 2_000_000]}),
            shares_outstanding=1_000_000_000,
            listing_date=listing,
            free_float=free_float,
            lnst_positive=True,
            audit_opinion="unqualified",
            hose_loai_khoi_vnallshare=(free_float is None),
            ky_cbtt_gan_nhat="07/2026" if free_float is None else None,
        )

    ds = [make(f"S{i:02d}", 100.0 - i, free_float=0.5) for i in range(44)]
    ds.append(make("HVN", 95.0, free_float=None))  # hang von hoa cao, chac chan <= 40
    r = build_vn30(ds, date(2026, 7, 1))
    assert "HVN" not in r.missing_data
    assert not any("HVN" in cb for cb in r.canh_bao)


# ---------------------------------------------------------------------------
# Uu tien nhan: mot ly do truot THUC CHAT thang "thieu du lieu"
# ---------------------------------------------------------------------------

def test_ma_truot_dut_khoat_thi_khong_gan_nhan_thieu_du_lieu():
    """Ma moi niem yet 1 thang truot Dieu 3.2 mot cach dut khoat; free float cua no
    khong the co (HOSE chua cong bo cho ma moi) va cung KHONG con y nghia gi.
    Gan nhan "Thiếu dữ liệu" o day la sai: bo sung du lieu cung khong doi ket qua."""
    manual = {"MOI": {"listing_date": date(2026, 6, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    ds = lap_stock_inputs(["MOI"], {"MOI": _daily()}, {"MOI": 1_000_000}, manual, [], {}, {})
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "MOI")
    assert dong["ket_luan"] == "Không đạt", dong["ket_luan"]


def test_ma_chi_truot_vi_thieu_du_lieu_van_gan_nhan_thieu_du_lieu():
    manual = {"CU": {"listing_date": date(2016, 1, 1), "warning_status": "none",
                     "audit_opinion": "unqualified"}}
    ds = lap_stock_inputs(["CU"], {"CU": _daily()}, {"CU": 1_000_000}, manual, [],
                          {"CU": 0.30}, {})
    r = build_vn30(ds, date(2026, 7, 1))
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    dong = next(d for d in kq["stocks"] if d["symbol"] == "CU")
    assert dong["ket_luan"] == "Thiếu dữ liệu"


def test_missing_data_trong_json_khong_liet_ke_ma_da_truot_dut_khoat():
    """Nhan o bang va danh sach "Thiếu dữ liệu" o cuoi trang phai NOI CUNG MOT
    DIEU. Ma moi niem yet 1 thang bi loai dut khoat theo Dieu 3.2, nen no khong
    thuoc danh sach "chua ket luan duoc vi thieu du lieu" du free float trong."""
    manual = {"MOI": {"listing_date": date(2026, 6, 1), "warning_status": "none",
                      "lnst_positive": True, "audit_opinion": "unqualified"}}
    ds = lap_stock_inputs(["MOI"], {"MOI": _daily()}, {"MOI": 1_000_000}, manual, [], {}, {})
    r = build_vn30(ds, date(2026, 7, 1))
    assert "MOI" in r.missing_data          # o tang du lieu van dung: free float trong
    kq = xuat_json(r, date(2026, 7, 1), "07/2026")
    assert "MOI" not in kq["missing_data"]  # nhung khong hien ra web nhu mot cho mu


def test_ma_dat_het_tieu_chi_nhung_khong_du_suat_khong_bi_ghi_la_khong_dat():
    """Ma nhu BVH vuot CA 5 buoc sang loc, chi thua vi 30 suat da day (Dieu 4.3.1.f).
    Ghi "Không đạt" cho no la sai su that - phai phan biet ro voi ma truot tieu chi."""
    from build import _ket_luan
    from rules.models import BasketResult, ScreenResult

    r = BasketResult()
    r.metrics["BVH"] = {"hose_loai_khoi_vnallshare": False}
    r.screens["BVH"] = [
        ScreenResult("BVH", b, "3.2", True, "đạt") for b in
        ("eligibility", "free_float", "liquidity", "vn30_liquidity", "profit")
    ]
    assert _ket_luan("BVH", r) == "Đạt tiêu chí, ngoài rổ"


# ---------------------------------------------------------------------------
# Dinh nghia chi tieu hien tren web
# ---------------------------------------------------------------------------

def _kq_json():
    ds = lap_stock_inputs(["ABC"], {"ABC": _daily()}, {"ABC": 1_000_000}, {}, [], {})
    return xuat_json(build_vn30(ds, date(2026, 7, 1)), date(2026, 7, 1), "07/2026")


def test_json_co_dinh_nghia_cho_moi_cot_so_lieu_va_moi_nhan():
    kq = _kq_json()
    assert "dinh_nghia" in kq
    khoa_cot = {c["khoa"] for c in kq["dinh_nghia"]["cot"]}
    # Dung dung ten truong nhu bang top 50 dang dung (site/app.js COT)
    assert {"gtvh_ty", "gtvh_f_ty", "gtgd_kl_ty", "klgd_kl", "turnover",
            "free_float", "gtvh_rank"} <= khoa_cot
    for c in kq["dinh_nghia"]["cot"]:
        assert c["ten"] and c["mo_ta"] and c["rule_ref"], c
    for n in kq["dinh_nghia"]["nhan"]:
        assert n["nhan"] and n["mo_ta"], n


def test_dinh_nghia_lay_nguong_tu_thresholds_khong_viet_cung():
    """Doi so trong rules/thresholds.yaml thi mo ta tren web phai doi theo -
    neu khong, trang se noi mot nguong khac voi nguong dang thuc su duoc ap dung."""
    from rules.thresholds import load_thresholds

    t = load_thresholds()
    kq = _kq_json()
    mo_ta = " ".join(c["mo_ta"] for c in kq["dinh_nghia"]["cot"])
    assert "300.000" in mo_ta                                     # min_klgd_kl_shares
    assert "30 tỷ" in mo_ta                                       # min_gtgd_kl_vnd
    assert "0,05%" in mo_ta and "0,04%" in mo_ta                  # min_turnover_*
    assert "10%" in mo_ta                                         # free_float.min_ratio
    assert "2.000 tỷ" in mo_ta and "2.500 tỷ" in mo_ta            # ngoai le 3.3.3
    assert str(t["lookback"]["months"]) in mo_ta                  # 12 thang


def test_dinh_nghia_phu_het_nhan_ket_luan_ma_ket_luan_sinh_ra():
    import re

    from build import __file__ as f
    from pathlib import Path

    than = Path(f).read_text(encoding="utf-8").split("def _ket_luan(")[1].split("\ndef ")[0]
    nhan_sinh_ra = set(re.findall(r'return "([^"]+)"', than))
    co_mo_ta = {n["nhan"] for n in _kq_json()["dinh_nghia"]["nhan"]}
    assert nhan_sinh_ra <= co_mo_ta, f"chưa giải thích nhãn: {nhan_sinh_ra - co_mo_ta}"
