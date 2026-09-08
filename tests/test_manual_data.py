import pytest

from collectors.manual_data import ManualDataError, load_manual

HOP_LE = """
VIC:
  listing_date: 2018-05
  warning_status: none
  lnst_positive: true
  audit_opinion: unqualified
"""


def _viet(tmp_path, noi_dung):
    p = tmp_path / "manual.yaml"
    p.write_text(noi_dung, encoding="utf-8")
    return p


def test_doc_duoc_file_hop_le(tmp_path):
    d = load_manual(_viet(tmp_path, HOP_LE))
    assert d["VIC"]["listing_date"].year == 2018
    assert d["VIC"]["listing_date"].month == 5
    assert d["VIC"]["lnst_positive"] is True
    assert d["VIC"]["audit_opinion"] == "unqualified"
    assert d["VIC"]["warning_status"] == "none"


def test_khong_con_truong_free_float(tmp_path):
    """free_float da chuyen sang nguon HOSE chinh thuc - manual.yaml khong con giu truong nay."""
    d = load_manual(_viet(tmp_path, HOP_LE))
    assert "free_float" not in d["VIC"]
    assert "free_float_source" not in d["VIC"]


def test_free_float_trong_yaml_bi_bo_qua_khong_dung(tmp_path):
    """Neu file cu con sot free_float, phai bao loi de tranh 2 nguon su that."""
    xau = HOP_LE + "  free_float: 0.30\n"
    with pytest.raises(ManualDataError, match="free_float"):
        load_manual(_viet(tmp_path, xau))


def test_listing_date_khong_bat_buoc(tmp_path):
    """listing_date la truong khong bat buoc (HOSE khong cong bo dang may doc duoc)."""
    xau = HOP_LE.replace("  listing_date: 2018-05\n", "")
    d = load_manual(_viet(tmp_path, xau))
    assert d["VIC"]["listing_date"] is None


def test_trang_thai_canh_bao_la_gia_tri_la_thi_bao_loi(tmp_path):
    xau = HOP_LE.replace("warning_status: none", "warning_status: linh_tinh")
    with pytest.raises(ManualDataError, match="warning_status"):
        load_manual(_viet(tmp_path, xau))


def test_file_rong_tra_dict_rong(tmp_path):
    assert load_manual(_viet(tmp_path, "")) == {}


def test_thieu_warning_status_thi_bao_loi(tmp_path):
    """warning_status là trường bắt buộc - không được suy diễn mặc định."""
    xau = HOP_LE.replace("  warning_status: none\n", "")
    with pytest.raises(ManualDataError, match="warning_status"):
        load_manual(_viet(tmp_path, xau))


def test_listing_date_nhieu_dash_thi_bao_loi(tmp_path):
    """Chuỗi ngày như '2018-05-05-rac' không được chấp nhận."""
    xau = HOP_LE.replace("listing_date: 2018-05", "listing_date: '2018-05-05-rac'")
    with pytest.raises(ManualDataError, match="listing_date"):
        load_manual(_viet(tmp_path, xau))
