"""Test doc cong bo chinh thuc HOSE (CBTT) - PDF that trong data/hose_index/."""
from pathlib import Path

import pytest

from collectors.hose_disclosure import HoseDisclosureError, doc_cbtt

PDF_KY_01_2026 = (
    Path(__file__).resolve().parent.parent / "data" / "hose_index" / "cbtt_hose_index_2026-01.pdf"
)
PDF_KY_07_2026 = (
    Path(__file__).resolve().parent.parent / "data" / "hose_index" / "cbtt_hose_index_2026-07.pdf"
)

VN30_KY_01_2026 = [
    "ACB", "BID", "CTG", "DGC", "FPT", "GAS", "GVR", "HDB", "HPG", "LPB",
    "MBB", "MSN", "MWG", "PLX", "SAB", "SHB", "SSB", "SSI", "STB", "TCB",
    "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VPL", "VRE",
]


def test_ky_suy_tu_ten_file():
    kq = doc_cbtt(PDF_KY_01_2026)
    assert kq["ky"] == "2026-01"


def test_vn30_dung_30_ma_dung_thu_tu():
    kq = doc_cbtt(PDF_KY_01_2026)
    assert len(kq["vn30"]) == 30
    assert kq["vn30"] == VN30_KY_01_2026


def test_vn30_du_phong_co_du_lieu():
    kq = doc_cbtt(PDF_KY_01_2026)
    assert len(kq["vn30_du_phong"]) >= 1
    assert "BSR" in kq["vn30_du_phong"]


def test_vnallshare_292_ma_co_free_float():
    kq = doc_cbtt(PDF_KY_01_2026)
    assert kq["so_ma_vnallshare"] == 292
    assert len(kq["free_float"]) == 292


def test_moc_free_float_dung():
    kq = doc_cbtt(PDF_KY_01_2026)
    ff = kq["free_float"]
    assert ff["VIC"] == pytest.approx(0.35)
    assert ff["VCB"] == pytest.approx(0.11)
    assert ff["GAS"] == pytest.approx(0.05)
    assert ff["GVR"] == pytest.approx(0.04)
    assert ff["BSR"] == pytest.approx(0.08)
    assert ff["DGC"] == pytest.approx(0.60)
    assert ff["SAB"] == pytest.approx(0.11)
    assert ff["SHB"] == pytest.approx(0.75)
    assert ff["VPL"] == pytest.approx(0.15)
    assert ff["FPT"] == pytest.approx(0.85)


def test_mch_tcx_khong_co_trong_free_float():
    """MCH va TCX chua vao VNAllshare tai ky 01/2026 - dung dung khong duoc bia."""
    kq = doc_cbtt(PDF_KY_01_2026)
    assert "MCH" not in kq["free_float"]
    assert "TCX" not in kq["free_float"]


def test_ne_vn30_sai_so_luong_thi_bao_loi(monkeypatch):
    """Neu HOSE doi layout khien VN30 khong ra dung 30 ma, phai nem loi ro rang."""
    import collectors.hose_disclosure as hd

    def gia_vn30_thieu(text):
        return ["ACB", "BID"]  # gia lap chi bat duoc 2 ma

    monkeypatch.setattr(hd, "_bien_ban_vn30", gia_vn30_thieu)
    with pytest.raises(HoseDisclosureError, match="VN30"):
        doc_cbtt(PDF_KY_01_2026)


def test_ne_free_float_ngoai_khoang_thi_bao_loi(monkeypatch):
    import collectors.hose_disclosure as hd

    orig = hd._bien_ban_vnallshare

    def gia_lap_sai(text):
        so_ma, ff = orig(text)
        ff["ACB"] = 1.5  # gia lap gia tri vo ly
        return so_ma, ff

    monkeypatch.setattr(hd, "_bien_ban_vnallshare", gia_lap_sai)
    with pytest.raises(HoseDisclosureError, match="free.float|free_float"):
        doc_cbtt(PDF_KY_01_2026)


# ---- Ky 07/2026: xac nhan xac dinh vung trang bang TIEU DE (khong bam so trang) ----
# Ky nay VNAllshare bat dau o trang index 9 (khac han ky 01/2026 la trang 11), va
# BSR (dang trong VN30 ky 07) truoc day bi thieu free-float do loi bam so trang cu.


def test_ky_07_vnallshare_boc_du_hon_han_212():
    """Loi cu (bam so trang cu 11-18) chi boc duoc 212 ma cho ky 07. Phai > 250."""
    kq = doc_cbtt(PDF_KY_07_2026)
    assert kq["so_ma_vnallshare"] > 250
    assert kq["so_ma_vnallshare"] == 303
    assert len(kq["free_float"]) == 303


def test_ky_07_bsr_co_free_float():
    """BSR dang trong VN30 ky 07/2026 - theo bat bien VN30 subset VNAllshare,
    BSR bat buoc phai co free-float trong VNAllshare."""
    kq = doc_cbtt(PDF_KY_07_2026)
    assert "BSR" in kq["vn30"]
    assert kq["free_float"]["BSR"] == pytest.approx(0.08)


def test_ky_07_mch_tcx_co_free_float():
    kq = doc_cbtt(PDF_KY_07_2026)
    assert kq["free_float"]["MCH"] == pytest.approx(0.20)
    assert kq["free_float"]["TCX"] == pytest.approx(0.15)


def test_moi_ma_vn30_ca_hai_ky_deu_co_free_float():
    """Bat bien VN30 subset VNAllshare phai dung cho MOI ky, khong chi ky 07."""
    for pdf in (PDF_KY_01_2026, PDF_KY_07_2026):
        kq = doc_cbtt(pdf)
        thieu = [ma for ma in kq["vn30"] if ma not in kq["free_float"]]
        assert thieu == [], f"{pdf.name}: cac ma VN30 thieu free-float: {thieu}"


def test_ne_vn30_thieu_free_float_thi_bao_loi(monkeypatch):
    """Kiem tra toan ven moi: gia lap 1 ma VN30 (BID) bi thieu free-float trong
    VNAllshare (vd do doc sai vung trang) - phai nem HoseDisclosureError ro rang,
    nham dung BID, thay vi am tham tra ve du lieu thieu."""
    import collectors.hose_disclosure as hd

    orig = hd._bien_ban_vnallshare

    def gia_lap_thieu_bid(text):
        so_ma, ff = orig(text)
        ff.pop("BID", None)
        return so_ma - 1, ff

    monkeypatch.setattr(hd, "_bien_ban_vnallshare", gia_lap_thieu_bid)
    with pytest.raises(HoseDisclosureError, match="BID"):
        doc_cbtt(PDF_KY_01_2026)
