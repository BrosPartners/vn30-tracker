"""Script dung mot lan: don cac file cache chuoi gia (daily-*) bi nhiem loi
"cache ket qua rong vinh vien" (xem sua loi trong collectors/market_data.cached()).

Truoc khi sua, moi lan fetch_daily() that bai (mang loi/rate-limit/timeout)
deu bi ghi xuong dia thanh {"records": []} - va vi cache cua so QUA KHU la
BAT BIEN (khong bao gio het han) nen loi nay khong bao gio tu khoi. Script
nay quet ca .cache/ (cache theo ngay) va .cache/lichsu/ (cache bat bien),
xoa moi file co dang {"records": []} (danh sach ban ghi rong), va in ra
danh sach ma bi anh huong de doi chieu.

Chay: python scripts/don_cache_rong.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"

# Chi xet file cache chuoi gia OHLCV (dang "daily-<MA>-...json"), tranh dong
# vao cac loai cache khac (hose-universe, shares-outstanding, current-market-cap,
# lnst...) vi cau truc JSON cua chung khac va "rong" co the la binh thuong.
MAU_TEN_FILE_DAILY = re.compile(r"^daily-([A-Z0-9]+)-")


def _la_cache_rong(duong_dan: Path) -> bool:
    """True neu file la cache chuoi gia va payload co danh sach records RONG."""
    if not MAU_TEN_FILE_DAILY.match(duong_dan.name):
        return False
    try:
        payload = json.loads(duong_dan.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(payload, dict) and payload.get("records") == []


def don_cache_rong(cache_dir: Path = CACHE_DIR) -> list[Path]:
    """Quet cache_dir va cache_dir/lichsu, xoa file cache chuoi gia rong, tra ve
    danh sach duong dan da xoa."""
    da_xoa: list[Path] = []
    thu_muc_can_quet = [cache_dir, cache_dir / "lichsu"]
    for thu_muc in thu_muc_can_quet:
        if not thu_muc.is_dir():
            continue
        for f in sorted(thu_muc.glob("*.json")):
            if _la_cache_rong(f):
                da_xoa.append(f)
                f.unlink()
    return da_xoa


def _ma_tu_ten_file(duong_dan: Path) -> str:
    m = MAU_TEN_FILE_DAILY.match(duong_dan.name)
    return m.group(1) if m else duong_dan.name


def main() -> None:
    da_xoa = don_cache_rong()
    if not da_xoa:
        print("Không có file cache rỗng nào cần dọn.")
        return
    ma_bi_anh_huong = sorted(set(_ma_tu_ten_file(f) for f in da_xoa))
    print(f"Đã xoá {len(da_xoa)} file cache rỗng, liên quan {len(ma_bi_anh_huong)} mã:")
    for ma in ma_bi_anh_huong:
        print(f"  - {ma}")
    print()
    print("Chi tiết từng file đã xoá:")
    for f in da_xoa:
        print(f"  {f}")


if __name__ == "__main__":
    main()
