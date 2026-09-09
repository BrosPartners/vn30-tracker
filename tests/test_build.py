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
    assert len(kq["xap_xi"]) == 5
    assert any("thỏa thuận" in x for x in kq["xap_xi"])


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
