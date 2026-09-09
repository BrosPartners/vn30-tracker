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
        "message", "shortfall", "thieu_du_lieu", "lnst_ty", "lnst_ky", "lnst_nguon", "niem_yet_nguon",
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


# ---------------------------------------------------------------------------
# Phan loai mau o bang top 50
# ---------------------------------------------------------------------------

NHAN_KET_LUAN = [
    "Trong rổ dự kiến",
    "Dự phòng",
    "Không đạt",
    "Đạt tiêu chí, ngoài rổ",
    "Thiếu dữ liệu",
    "HOSE loại khỏi VNAllshare",
]


def test_moi_nhan_ket_luan_deu_co_mau_rieng_trong_app_js():
    """Bat truong hop them nhan moi trong build._ket_luan ma quen to mau -
    dong do se hien mau trung voi nhan khac, nguoi doc hieu sai."""
    js = APP_JS.read_text(encoding="utf-8")
    build_py = (ROOT / "build.py").read_text(encoding="utf-8")
    for nhan in NHAN_KET_LUAN:
        assert nhan in build_py, f"build.py không còn sinh nhãn '{nhan}'"
        assert nhan in js, f"app.js chưa gán màu cho nhãn '{nhan}'"


def test_build_py_khong_sinh_nhan_ket_luan_la():
    """Moi nhan tra ve tu _ket_luan phai nam trong bang mau - khong duoc phat sinh
    nhan thu 6 ma trang khong biet to mau."""
    import re

    build_py = (ROOT / "build.py").read_text(encoding="utf-8")
    than = build_py.split("def _ket_luan(")[1].split("\ndef ")[0]
    for nhan in re.findall(r'return "([^"]+)"', than):
        assert nhan in NHAN_KET_LUAN, f"_ket_luan sinh nhãn lạ '{nhan}'"


def test_dong_bang_duoc_gan_class_theo_ket_luan():
    js = APP_JS.read_text(encoding="utf-8")
    assert "tr.className" in js or "tr.classList" in js, \
        "Các dòng của bảng top 50 phải được gán class để phân loại màu"


def test_css_dinh_nghia_du_5_lop_mau():
    css = (ROOT / "site" / "style.css").read_text(encoding="utf-8")
    for lop in ("kl-trong-ro", "kl-du-phong", "kl-khong-dat", "kl-dat-ngoai-ro",
                "kl-thieu-du-lieu", "kl-hose-loai"):
        assert lop in css, f"style.css thiếu định nghĩa màu cho .{lop}"


def test_trang_co_chu_giai_mau():
    """Mau khong tu giai thich duoc - phai co chu giai, va khong duoc chi dua vao
    mau (nguoi mu mau/in den trang): moi dong bang van co cot 'Kết luận' bang chu."""
    html = INDEX.read_text(encoding="utf-8")
    assert "chu-giai" in html, "Bảng top 50 phải có chú giải màu"
    js = APP_JS.read_text(encoding="utf-8")
    assert '"ket_luan", "Kết luận"' in js, "Cột 'Kết luận' bằng chữ phải được giữ lại"


def test_tieu_de_trang_la_tracking_vn30():
    html = INDEX.read_text(encoding="utf-8")
    assert "<title>Tracking VN30" in html
    assert "<h1>Tracking VN30</h1>" in html
