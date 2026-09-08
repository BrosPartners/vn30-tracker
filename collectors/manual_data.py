"""Doc data/manual.yaml - phan du lieu BAT BUOC do nguoi xac nhan.

Free float KHONG con nam o day - da chuyen sang nguon cong bo chinh thuc cua HOSE
(collectors/hose_disclosure.py, doc tu PDF CBTT, ket qua o data/hose_index/*.yaml).
manual.yaml chi con giu nhung gi HOSE khong cong bo o dang may doc duoc:
lnst_positive, audit_opinion, warning_status (bat buoc), va listing_date (khong bat buoc).

Nguyen tac: tha bao loi con hon doan. Neu file con sot truong free_float (tu thoi
truoc khi chuyen nguon), bao loi ro rang de tranh hai nguon su that thay vi am
tham bo qua.
"""
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

TRANG_THAI_HOP_LE = {"none", "warning", "control", "restricted", "suspended"}
Y_KIEN_HOP_LE = {"unqualified", "qualified", "unknown"}
BAT_BUOC = ("lnst_positive", "audit_opinion", "warning_status")
# free_float/free_float_source da chuyen nguon - neu con sot trong file thi bao loi
# thay vi am tham dung, tranh hai nguon su that (xem hose_disclosure.py)
KHOA_DA_BO = ("free_float", "free_float_source")


class ManualDataError(ValueError):
    """File manual.yaml sai dinh dang hoac gia tri vo ly."""


def _doc_thang(gia_tri, symbol: str) -> Optional[date]:
    """Chap nhan '2018-05' (YYYY-MM) hoac ngay day du, hoac None neu khong co."""
    if gia_tri is None:
        return None
    if isinstance(gia_tri, date):
        return gia_tri
    try:
        # Chuỗi phải chính xác dạng YYYY-MM (2 phần), không được nhiều hơn
        parts = str(gia_tri).split("-")
        if len(parts) != 2:
            raise ManualDataError(
                f"{symbol}: listing_date '{gia_tri}' phải là ngày (YYYY-MM-DD) hoặc tháng (YYYY-MM), "
                f"không được chuỗi tùy ý"
            )
        nam, thang = parts
        return date(int(nam), int(thang), 1)
    except ManualDataError:
        raise
    except Exception as e:
        raise ManualDataError(f"{symbol}: listing_date '{gia_tri}' không đọc được") from e


def load_manual(path: Path) -> dict[str, dict]:
    with Path(path).open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    out: dict[str, dict] = {}
    for symbol, ban_ghi in raw.items():
        if not isinstance(ban_ghi, dict):
            raise ManualDataError(f"{symbol}: bản ghi phải là một khối key: value")

        for khoa in KHOA_DA_BO:
            if khoa in ban_ghi:
                raise ManualDataError(
                    f"{symbol}: trường '{khoa}' không còn dùng ở manual.yaml — "
                    f"free float nay lay tu công bố chính thức HOSE (data/hose_index/*.yaml), "
                    f"xóa trường này khỏi manual.yaml để tránh hai nguồn sự thật"
                )

        for khoa in BAT_BUOC:
            if khoa not in ban_ghi:
                raise ManualDataError(f"{symbol}: thiếu trường bắt buộc '{khoa}'")

        tt = ban_ghi["warning_status"]
        if tt not in TRANG_THAI_HOP_LE:
            raise ManualDataError(
                f"{symbol}: warning_status '{tt}' không hợp lệ, phải thuộc {sorted(TRANG_THAI_HOP_LE)}")

        yk = ban_ghi.get("audit_opinion", "unknown")
        if yk not in Y_KIEN_HOP_LE:
            raise ManualDataError(f"{symbol}: audit_opinion '{yk}' không hợp lệ")

        out[symbol.upper()] = {
            "listing_date": _doc_thang(ban_ghi.get("listing_date"), symbol),
            "warning_status": tt,
            "lnst_positive": ban_ghi.get("lnst_positive"),
            "audit_opinion": yk,
        }
    return out
