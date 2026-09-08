"""Kiem tra trang web khong lech khoi hop dong du lieu cua latest.json."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_JS = ROOT / "site" / "app.js"
INDEX = ROOT / "site" / "index.html"


def test_app_js_chi_dung_truong_co_that_trong_json():
    """Bat loi go sai ten truong - loi nay khong bao gi, chi hien o man hinh trong."""
    hop_le = {
        "as_of", "ky_review", "constituents", "reserve", "missing_data", "stocks",
        "xap_xi", "nguon_quy_tac", "symbol", "gtvh_rank", "gtvh_ty", "gtvh_f_ty",
        "gtgd_kl_ty", "klgd_kl", "turnover", "free_float", "free_float_rounded",
        "in_previous_basket", "ket_luan", "canh_bao", "screens", "step", "rule_ref", "passed",
        "message", "shortfall", "lnst_ty", "lnst_ky", "lnst_nguon", "niem_yet_nguon",
        "niem_yet_thang", "lich", "lich_su", "ky", "ngay_chot", "ngay_hieu_luc", "ngay",
        "gtvh_rank", "gtgd_kl_ty",
    }
    js = APP_JS.read_text(encoding="utf-8")
    for truong in re.findall(r"\bd(?:ata)?\.([a-z_]+)\b", js):
        assert truong in hop_le, f"app.js dùng trường '{truong}' không có trong latest.json"


def test_trang_hien_canh_bao_xap_xi():
    assert "xap_xi" in APP_JS.read_text(encoding="utf-8"), "Trang phải hiển thị các xấp xỉ"


def test_trang_khong_dung_thu_vien_ngoai():
    """Portal la site tinh thuan, khong framework - giu dung nguyen tac do."""
    html = INDEX.read_text(encoding="utf-8")
    assert "cdn" not in html.lower()
    assert "<script src=\"./app.js\"></script>" in html


def test_trang_khong_dung_thu_vien_ngoai_trong_css():
    css = (ROOT / "site" / "style.css").read_text(encoding="utf-8")
    assert "@import" not in css or "fonts.googleapis" in css


def test_trang_co_khoi_cuon_ngang_cho_bang():
    css = (ROOT / "site" / "style.css").read_text(encoding="utf-8")
    assert "overflow-x" in css
