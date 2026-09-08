import pytest

from collectors.manual_data import ManualDataError, load_manual

HOP_LE = """
VIC:
  free_float: 0.30
  free_float_source: "DNSE 2026-09-05"
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
    assert d["VIC"]["free_float"] == 0.30
    assert d["VIC"]["listing_date"].year == 2018
    assert d["VIC"]["listing_date"].month == 5


def test_free_float_ngoai_khoang_0_1_thi_bao_loi(tmp_path):
    xau = HOP_LE.replace("free_float: 0.30", "free_float: 30")
    with pytest.raises(ManualDataError, match="free_float"):
        load_manual(_viet(tmp_path, xau))


def test_thieu_nguon_free_float_thi_bao_loi(tmp_path):
    """Moi con so nhap tay phai co nguon va ngay - de con kiem chung lai."""
    xau = HOP_LE.replace('  free_float_source: "DNSE 2026-09-05"\n', "")
    with pytest.raises(ManualDataError, match="free_float_source"):
        load_manual(_viet(tmp_path, xau))


def test_trang_thai_canh_bao_la_gia_tri_la_thi_bao_loi(tmp_path):
    xau = HOP_LE.replace("warning_status: none", "warning_status: linh_tinh")
    with pytest.raises(ManualDataError, match="warning_status"):
        load_manual(_viet(tmp_path, xau))


def test_file_rong_tra_dict_rong(tmp_path):
    assert load_manual(_viet(tmp_path, "")) == {}
