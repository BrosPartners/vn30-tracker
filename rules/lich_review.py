"""Lich review cua HOSE-Index (Index Summary, Ground Rules v4.0).

- Thay doi ro: thu Tu tuan thu 3 cua thang 1 va thang 7.
- Hieu luc: thu Hai dau tien cua thang 2, 8 (tuong ung voi ky thang 1, 7).
"""
from calendar import Calendar
from datetime import date

THU_TU, THU_HAI = 2, 0


def _cac_ngay_theo_thu(nam: int, thang: int, thu: int) -> list[date]:
    return [d for d in Calendar().itermonthdates(nam, thang)
            if d.month == thang and d.weekday() == thu]


def thu_tu_trong_thang(nam: int, thang: int, thu_may: int) -> date:
    """Thu Tu thu N cua thang (thu_may = 3 nghia la tuan thu 3)."""
    return _cac_ngay_theo_thu(nam, thang, THU_TU)[thu_may - 1]


def thu_hai_dau_tien(nam: int, thang: int) -> date:
    return _cac_ngay_theo_thu(nam, thang, THU_HAI)[0]


def ngay_chot_tu_ky(ky: str) -> date:
    """Ngay chot du lieu cua MOT ky cong bo da biet (khong phai ky ke tiep).

    ky la chuoi "YYYY-MM" dung format luu trong data/hose_index/<ky>.yaml (vd
    "2026-07" cho ky thang 7/2026). Dung ham nay khi da co san ky cong bo (vd
    ky_cbtt tra ve tu build.load_free_float_moi_nhat) va can biet HOSE da CHOT
    du lieu ngay nao de doi chieu voi ngay giao dich/niem yet cua mot ma - xem
    build.py, lap_stock_inputs (phan biet "HOSE da xet va loai" voi "thieu du
    lieu thuc su").
    """
    nam, thang = (int(x) for x in ky.split("-"))
    return thu_tu_trong_thang(nam, thang, 3)


def ky_review_ke_tiep(hom_nay: date) -> dict:
    """Ky review gan nhat con o phia truoc, tinh theo ngay chot du lieu."""
    ung_vien = []
    for nam in (hom_nay.year, hom_nay.year + 1):
        for thang, thang_hieu_luc, nam_hieu_luc in ((1, 2, nam), (7, 8, nam)):
            ung_vien.append({
                "ky": f"{thang:02d}/{nam}",
                "ngay_chot": thu_tu_trong_thang(nam, thang, 3),
                "ngay_hieu_luc": thu_hai_dau_tien(nam_hieu_luc, thang_hieu_luc),
            })
    return min((k for k in ung_vien if k["ngay_chot"] >= hom_nay),
               key=lambda k: k["ngay_chot"])
