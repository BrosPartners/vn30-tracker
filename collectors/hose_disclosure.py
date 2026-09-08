"""Doc cong bo chinh thuc HOSE (CBTT) ve danh muc chi so + free-float tu PDF.

Nguon: HOSE tu cong bo free-float chinh thuc moi quy cho toan bo VNAllshare -
dung so nay thay vi nhap tay tu DNSE. File PDF (static2.vietstock.vn) duoc luu
o data/hose_index/cbtt_hose_index_<ky>.pdf va commit vao repo lam bang chung goc.

Cau truc file (kiem chung tren ky 01/2026, 28 trang):
- Trang 1 (index 0): danh muc VN30 (30 ma) + danh muc du phong VN30 ben duoi.
- Trang 12-18 (index 11..17): VNALLSHARE - moi ma kem ty le free-float lam tron.

collectors/ KHONG duoc import gi tu rules/ - module nay chi doc va tra ve dict thuan.

Nguyen tac: tha bao loi con hon am tham ra du lieu thieu/sai. Neu HOSE doi layout
PDF, ham phai nem HoseDisclosureError ngay thay vi tra ve danh sach cut/rong.
"""
import re
from pathlib import Path

import fitz  # PyMuPDF

# Bieu thuc chinh quy bat 1 dong bang: stt, ma 3 chu, ten cong ty, KLLH tinh chi so,
# ty le free-float lam tron (%). Dung lookahead (?=\n) o cuoi de KHONG "an" dau \n
# ket thuc dong - neu khong, dong tiep theo se mat di \n dan dau va bi bo lot khoi
# ket qua tim kiem (da xac minh: thieu EIB, MSB trong danh muc du phong neu tieu \n).
_PATTERN_DONG = re.compile(
    r"\n(\d{1,3})\n([A-Z]{3})\n(.*?)\n\s*([\d,]{7,})\s*\n\s*(\d{1,3})%(?=\n)", re.S
)

TRANG_VN30 = 0            # index trang chua VN30 + du phong VN30
TRANG_VNALLSHARE_TU = 11  # index trang bat dau VNALLSHARE
TRANG_VNALLSHARE_DEN = 18 # index trang ket thuc (khong bao gom) VNALLSHARE

SO_MA_VN30 = 30
SO_MA_VNALLSHARE_TOI_THIEU = 200  # duoi nguong nay coi la loi doc PDF/doi layout


class HoseDisclosureError(ValueError):
    """PDF cong bo HOSE khong doc duoc dung dinh dang mong doi (vd HOSE doi layout)."""


def _bien_ban_vn30(text: str) -> tuple[list[str], list[str]]:
    """Tach danh muc VN30 chinh thuc va danh muc du phong tu text trang 1.

    Luu y: PDF co bo cuc 2 bang canh nhau (VN30 + du phong), nen thu tu TEXT trich
    ra khong theo dung thu tu THI GIAC - dong tieu de "Danh mục cổ phiếu dự phòng"
    co the xuat hien SAU ca cac dong du lieu du phong trong text (da kiem chung).
    Vi vay KHONG dung vi tri tieu de de cat, ma dung quy uoc: SO_MA_VN30 dong dau
    tien khop pattern la VN30 chinh thuc (theo dung thu tu trong file), phan con
    lai la du phong.
    """
    tat_ca = [mo.group(2) for mo in _PATTERN_DONG.finditer(text)]
    return tat_ca[:SO_MA_VN30], tat_ca[SO_MA_VN30:]


def _bien_ban_vnallshare(text: str) -> tuple[int, dict[str, float]]:
    """Bien ban danh muc VNALLSHARE: tra ve (so ma, dict ma -> free-float thap phan)."""
    free_float: dict[str, float] = {}
    for mo in _PATTERN_DONG.finditer(text):
        ma = mo.group(2)
        ty_le_phan_tram = int(mo.group(5))
        free_float[ma] = ty_le_phan_tram / 100.0
    return len(free_float), free_float


def _suy_ky_tu_ten_file(pdf_path: Path) -> str:
    """Suy ky cong bo (vd '2026-01') tu ten file cbtt_hose_index_2026-01.pdf."""
    m = re.search(r"(\d{4}-\d{2})", pdf_path.stem)
    if not m:
        raise HoseDisclosureError(
            f"Không suy được kỳ công bố từ tên file '{pdf_path.name}' "
            f"(cần dạng cbtt_hose_index_YYYY-MM.pdf)"
        )
    return m.group(1)


def doc_cbtt(pdf_path: Path) -> dict:
    """Doc file cong bo chinh thuc HOSE, tra ve dict:
    - ky: chuoi ky (vd "2026-01")
    - vn30: danh sach 30 ma, giu dung thu tu trong file
    - vn30_du_phong: danh sach ma du phong
    - free_float: dict ma -> ty le free-float (0-1), tu danh muc VNALLSHARE
    - so_ma_vnallshare: so nguyen ma bat duoc trong VNALLSHARE

    Nem HoseDisclosureError neu du lieu boc ra bat thuong (HOSE doi layout PDF).
    """
    pdf_path = Path(pdf_path)
    ky = _suy_ky_tu_ten_file(pdf_path)

    doc = fitz.open(pdf_path)
    try:
        text_vn30 = doc[TRANG_VN30].get_text()
        text_vnallshare = "".join(
            doc[i].get_text() for i in range(TRANG_VNALLSHARE_TU, min(TRANG_VNALLSHARE_DEN, len(doc)))
        )
    finally:
        doc.close()

    vn30, vn30_du_phong = _bien_ban_vn30(text_vn30)
    so_ma_vnallshare, free_float = _bien_ban_vnallshare(text_vnallshare)

    if len(vn30) != SO_MA_VN30:
        raise HoseDisclosureError(
            f"Kỳ {ky}: danh mục VN30 bóc được {len(vn30)} mã, không đúng {SO_MA_VN30} mã "
            f"kỳ vọng — có thể HOSE đã đổi layout PDF, kiểm tra lại _bien_ban_vn30()"
        )

    if so_ma_vnallshare < SO_MA_VNALLSHARE_TOI_THIEU:
        raise HoseDisclosureError(
            f"Kỳ {ky}: danh mục VNALLSHARE chỉ bóc được {so_ma_vnallshare} mã "
            f"(dưới ngưỡng tối thiểu {SO_MA_VNALLSHARE_TOI_THIEU}) — có thể HOSE đã đổi "
            f"layout PDF hoặc phạm vi trang không còn đúng, kiểm tra lại TRANG_VNALLSHARE_TU/DEN"
        )

    for ma, ty_le in free_float.items():
        if not 0 <= ty_le <= 1:
            raise HoseDisclosureError(
                f"Kỳ {ky}: mã {ma} có free_float = {ty_le} nằm ngoài khoảng 0-1 — "
                f"dữ liệu bóc từ PDF có vẻ sai, không được dùng"
            )

    return {
        "ky": ky,
        "vn30": vn30,
        "vn30_du_phong": vn30_du_phong,
        "free_float": free_float,
        "so_ma_vnallshare": so_ma_vnallshare,
    }
