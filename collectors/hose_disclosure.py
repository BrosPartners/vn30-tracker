"""Doc cong bo chinh thuc HOSE (CBTT) ve danh muc chi so + free-float tu PDF.

Nguon: HOSE tu cong bo free-float chinh thuc moi quy cho toan bo VNAllshare -
dung so nay thay vi nhap tay tu DNSE. File PDF (static2.vietstock.vn) duoc luu
o data/hose_index/cbtt_hose_index_<ky>.pdf va commit vao repo lam bang chung goc.

QUAN TRONG - KHONG duoc bam theo SO TRANG: moi ky cong bo co so trang khac nhau
cho tung muc (da xac minh thuc te: ky 01/2026 muc VNALLSHARE bat dau o trang
index 11, nhung ky 07/2026 lai bat dau o trang index 9 - lech 2 trang vi cac
muc truoc do (VN100/VNSMALLCAP...) co so trang khac nhau giua 2 ky). Neu ham
bam so trang hard-code, ket qua se sai lech ma khong bao loi (vi dinh dang
tung dong van dung, chi la doc nham muc) - day chinh la loi da xay ra trong
thuc te khien ky 07/2026 chi boc duoc 212/303 ma VNAllshare va thieu free-float
cua BSR (mot ma dang trong VN30, ve nguyen tac VN30 luon la tap con VNAllshare).

Cach lam DUNG: moi trang mo dau 1 muc trong PDF co dong tieu de dang
"CÔNG BỐ THÔNG TIN DANH MỤC CỔ PHIẾU THÀNH PHẦN (CỦA) CHỈ SỐ <TEN_CHI_SO>"
nam o footer cua chinh trang do (PyMuPDF doc no o cuoi text trang). Ham quet
toan bo trang, tim trang co tieu de chua ten chi so muc tieu, roi lay tu trang
do cho toi ngay truoc trang co tieu de cua muc KE TIEP (bat ke muc gi).

Luu y rieng cho VNALLSHARE: chuoi "VNALLSHARE" cung xuat hien trong tieu de cua
muc chi so nganh ngay sau do, dang "... CÁC CHỈ SỐ NGÀNH VNALLSHARE SECTOR
INDICES" - phai loai tru bang tu khoa "NGÀNH"/"SECTOR" thi moi phan biet duoc
voi tieu de muc VNALLSHARE that ("... CHỈ SỐ VNALLSHARE").

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

# Neo nhan dien 1 trang "tieu de muc" - dong nay xuat hien o cuoi moi trang
# mo dau 1 muc trong PDF cong bo HOSE (VN30, VNMIDCAP, VN100, VNSMALLCAP,
# VNALLSHARE, cac chi so nganh VNAllshare...).
_NEO_TIEU_DE_MUC = "CÔNG BỐ THÔNG TIN"
_TU_KHOA_VN30 = "VN30"
_TU_KHOA_VNALLSHARE = "VNALLSHARE"
# Tieu de muc chi so nganh cung chua chuoi "VNALLSHARE" nen phai loai tru rieng
_TU_LOAI_TRU_VNALLSHARE = ("NGÀNH", "SECTOR")

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


def _tim_trang_tieu_de(doc: "fitz.Document", tu_khoa: str, loai_tru: tuple = ()) -> int | None:
    """Tim trang DAU TIEN co dong tieu de muc (neo _NEO_TIEU_DE_MUC) chua tu_khoa
    va KHONG chua bat ky tu nao trong loai_tru. Tra ve None neu khong tim thay
    (goi noi con lai tu HoseDisclosureError ro rang thay vi doan bua trang nao do).
    """
    for i in range(len(doc)):
        text = doc[i].get_text()
        vi_tri = text.find(_NEO_TIEU_DE_MUC)
        if vi_tri == -1:
            continue
        tieu_de = text[vi_tri : vi_tri + 200]
        if tu_khoa in tieu_de and not any(tu in tieu_de for tu in loai_tru):
            return i
    return None


def _tim_trang_tieu_de_ke_tiep(doc: "fitz.Document", tu_trang: int) -> int:
    """Tim trang tiep theo (sau tu_trang) co dong tieu de cua BAT KY muc nao
    khac - dung de xac dinh diem KET THUC cua muc bat dau tai tu_trang. Neu
    khong con muc nao nua, tra ve len(doc) (lay het cac trang con lai).
    """
    for i in range(tu_trang + 1, len(doc)):
        if _NEO_TIEU_DE_MUC in doc[i].get_text():
            return i
    return len(doc)


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
        trang_vn30 = _tim_trang_tieu_de(doc, _TU_KHOA_VN30)
        if trang_vn30 is None:
            raise HoseDisclosureError(
                f"Kỳ {ky}: không tìm thấy trang có tiêu đề mục VN30 trong PDF — "
                f"có thể HOSE đã đổi cách trình bày tiêu đề, kiểm tra lại _tim_trang_tieu_de()"
            )

        trang_vnallshare_tu = _tim_trang_tieu_de(
            doc, _TU_KHOA_VNALLSHARE, loai_tru=_TU_LOAI_TRU_VNALLSHARE
        )
        if trang_vnallshare_tu is None:
            raise HoseDisclosureError(
                f"Kỳ {ky}: không tìm thấy trang có tiêu đề mục VNALLSHARE trong PDF — "
                f"có thể HOSE đã đổi cách trình bày tiêu đề, kiểm tra lại _tim_trang_tieu_de()"
            )
        trang_vnallshare_den = _tim_trang_tieu_de_ke_tiep(doc, trang_vnallshare_tu)

        text_vn30 = doc[trang_vn30].get_text()
        text_vnallshare = "".join(
            doc[i].get_text() for i in range(trang_vnallshare_tu, trang_vnallshare_den)
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

    # Kiem tra bat bien quan trong nhat: VN30 la tap con cua VNAllshare theo dung
    # quy tac chi so HOSE, nen bat ky ma VN30 nao thieu free-float trong VNAllshare
    # chac chan la loi doc PDF (vd xac dinh sai vung trang VNALLSHARE), khong phai
    # dac diem du lieu that. Kiem tra nay bat duoc loi ma nguong dem so ma (o tren)
    # khong bat duoc, vi so ma bot con lai co the van > SO_MA_VNALLSHARE_TOI_THIEU.
    ma_thieu_free_float = [ma for ma in vn30 if ma not in free_float]
    if ma_thieu_free_float:
        raise HoseDisclosureError(
            f"Kỳ {ky}: các mã VN30 sau đây KHÔNG có free-float trong VNALLSHARE: "
            f"{', '.join(ma_thieu_free_float)} — điều này bất khả thi vì VN30 luôn "
            f"là tập con của VNALLSHARE, chắc chắn là lỗi đọc PDF (vùng trang "
            f"VNALLSHARE xác định sai), kiểm tra lại _tim_trang_tieu_de()"
        )

    return {
        "ky": ky,
        "vn30": vn30,
        "vn30_du_phong": vn30_du_phong,
        "free_float": free_float,
        "so_ma_vnallshare": so_ma_vnallshare,
    }
