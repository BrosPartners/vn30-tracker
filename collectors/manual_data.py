"""Doc data/manual.yaml - phan du lieu BAT BUOC do nguoi xac nhan.

Nguyen tac: tha bao loi con hon doan. Thieu free float thi de None va bao ra ngoai,
tuyet doi khong suy dien.
"""
from datetime import date
from pathlib import Path

import yaml

TRANG_THAI_HOP_LE = {"none", "warning", "control", "restricted", "suspended"}
Y_KIEN_HOP_LE = {"unqualified", "qualified", "unknown"}
BAT_BUOC = ("free_float", "free_float_source", "listing_date")


class ManualDataError(ValueError):
    """File manual.yaml sai dinh dang hoac gia tri vo ly."""


def _doc_thang(gia_tri, symbol: str) -> date:
    """Chap nhan '2018-05' (YYYY-MM) hoac ngay day du."""
    if isinstance(gia_tri, date):
        return gia_tri
    try:
        nam, thang = str(gia_tri).split("-")[:2]
        return date(int(nam), int(thang), 1)
    except Exception as e:
        raise ManualDataError(f"{symbol}: listing_date '{gia_tri}' không đọc được") from e


def load_manual(path: Path) -> dict[str, dict]:
    with Path(path).open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    out: dict[str, dict] = {}
    for symbol, ban_ghi in raw.items():
        if not isinstance(ban_ghi, dict):
            raise ManualDataError(f"{symbol}: bản ghi phải là một khối key: value")

        for khoa in BAT_BUOC:
            if khoa not in ban_ghi:
                raise ManualDataError(f"{symbol}: thiếu trường bắt buộc '{khoa}'")

        f_ff = ban_ghi["free_float"]
        if not isinstance(f_ff, (int, float)) or not 0 <= f_ff <= 1:
            raise ManualDataError(
                f"{symbol}: free_float phải là tỷ lệ trong khoảng 0–1, đang là {f_ff!r}")

        tt = ban_ghi.get("warning_status", "none")
        if tt not in TRANG_THAI_HOP_LE:
            raise ManualDataError(
                f"{symbol}: warning_status '{tt}' không hợp lệ, phải thuộc {sorted(TRANG_THAI_HOP_LE)}")

        yk = ban_ghi.get("audit_opinion", "unknown")
        if yk not in Y_KIEN_HOP_LE:
            raise ManualDataError(f"{symbol}: audit_opinion '{yk}' không hợp lệ")

        out[symbol.upper()] = {
            "free_float": float(f_ff),
            "free_float_source": ban_ghi["free_float_source"],
            "listing_date": _doc_thang(ban_ghi["listing_date"], symbol),
            "warning_status": tt,
            "lnst_positive": ban_ghi.get("lnst_positive"),
            "audit_opinion": yk,
        }
    return out
