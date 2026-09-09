"""Script DUNG MOT LAN: chuyen cache fetch_daily() cua cua so gia QUA KHU DA CHOT
(end < hom nay) tu quy uoc cache theo-ngay cu (.cache/daily-<ma>-<start>-<end>-<ngay
chay>.json) sang quy uoc cache BAT BIEN moi (.cache/lichsu/daily-<ma>-<start>-<end>.json,
xem collectors/market_data.py::cached()).

Ly do: truoc khi sua, moi ngay chay lai bai kiem dinh doi chieu ro that la mat cache
va phai tai lai TOAN BO ~400 ma tu vnstock (de vuong RateLimitExceeded), du du lieu
cua cua so qua khu nay khong bao gio doi nua. File cache cu da co san tu cac lan
chay truoc - script nay tan dung lai thay vi vut di roi tai lai.

Quy tac chon file khi co nhieu ban (chay nhieu ngay khac nhau) cho CUNG 1 khoa
(ma, start, end): lay ban co ngay chay MOI NHAT (it kha nang bi loi/thieu du lieu
hon do vnstock cap nhat lien tuc cac phien gan nhat truoc do).

Khong xoa file cache-theo-ngay cu (an toan, de doi chieu neu can) - chi SAO CHEP
sang vi tri moi. Chay lai script nhieu lan la AN TOAN (bo qua ma da co ban bat bien).

Chay: python scripts/di_chuyen_cache_lich_su.py
"""
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache"
LICH_SU_DIR = CACHE_DIR / "lichsu"

# Khop dung quy uoc khoa cache hien tai cua fetch_daily(): "daily-<ma>-<start>-<end>"
# roi cached() gan them "-<ngay chay>.json" o cuoi.
MAU_TEN_FILE = re.compile(
    r"^daily-(?P<ma>[A-Z0-9]+)-(?P<start>\d{4}-\d{2}-\d{2})-(?P<end>\d{4}-\d{2}-\d{2})"
    r"-(?P<ngay_chay>\d{4}-\d{2}-\d{2})\.json$"
)


def main() -> None:
    if not CACHE_DIR.exists():
        print(f"Khong thay {CACHE_DIR}, khong co gi de chuyen.")
        return

    hom_nay = date.today()
    # nhom cac file theo khoa bat bien (ma, start, end), giu lai ban ngay chay moi nhat
    nhom: dict[tuple[str, str, str], tuple[str, Path]] = {}

    for p in CACHE_DIR.iterdir():
        if not p.is_file():
            continue
        m = MAU_TEN_FILE.match(p.name)
        if not m:
            continue
        end = date.fromisoformat(m.group("end"))
        if end >= hom_nay:
            continue  # cua so con "song" (hom nay/tuong lai) - khong phai bat bien, bo qua
        khoa = (m.group("ma"), m.group("start"), m.group("end"))
        ngay_chay = m.group("ngay_chay")
        hien_co = nhom.get(khoa)
        if hien_co is None or ngay_chay > hien_co[0]:
            nhom[khoa] = (ngay_chay, p)

    if not nhom:
        print("Khong tim thay file cache nao cua cua so qua khu da chot de chuyen.")
        return

    LICH_SU_DIR.mkdir(parents=True, exist_ok=True)
    da_chuyen = 0
    da_co_san = 0
    loi = 0
    for (ma, start, end), (_ngay_chay, p_nguon) in sorted(nhom.items()):
        khoa_cache = f"daily-{ma}-{start}-{end}"
        p_dich = LICH_SU_DIR / f"{khoa_cache}.json"
        if p_dich.exists():
            da_co_san += 1
            continue
        try:
            noi_dung = json.loads(p_nguon.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  BO QUA {p_nguon.name}: doc/parse loi ({e})")
            loi += 1
            continue
        p_dich.write_text(json.dumps(noi_dung, ensure_ascii=False), encoding="utf-8")
        da_chuyen += 1

    print(
        f"Da chuyen {da_chuyen} ma sang cache bat bien tai {LICH_SU_DIR} "
        f"(da co san tu truoc: {da_co_san}, loi: {loi}, tong nhom xet: {len(nhom)})."
    )


if __name__ == "__main__":
    main()
