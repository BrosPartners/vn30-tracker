"""Adapter vnstock - tang duy nhat cham mang.

Cache theo NGAY: file .cache/<key>-<YYYY-MM-DD>.json. Chay lai trong ngay thi
khong goi mang, sang hom sau tu dong lay moi. Moi ham fetch tu sinh khoa cache
tu day du tham so cua no, nguoi goi khong phai nghi ve khoa.
"""
import hashlib
import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
COT_CAN = ("time", "close", "volume")

# Cac hang so cau hinh - dua len day de de chinh, tranh hard-code ram trong ham
BATCH_SIZE_SHARES = 50  # so ma moi lo khi goi price_board, tranh timeout
HOSE_EXCHANGES = ["HOSE", "HSX"]  # ten san duoc coi la HOSE (vnstock tra ca 2 dang)
VNSTOCK_SOURCE = "VCI"  # nguon du lieu vnstock, dung thong nhat 1 cach viet

# vnstock ban cong dong gioi han ~60 request/phut, va khi vuot nguong no THOAT
# TIEN TRINH CUNG (os._exit) chu khong nem exception de try/except bat duoc.
# Vi vay phai TU DIEU TIET truoc khi goi, chu khong the "xu ly loi sau" duoc.
# Dat duoi 60 de co bien an toan (jitter, dem sai lech, request khac dang chay).
GIOI_HAN_REQUEST_MOI_PHUT = 55
CUA_SO_DIEU_TIET_GIAY = 60.0

# Bien moi truong de tat han che trong test (test khong duoc ngu that)
ENV_TAT_THROTTLE = "VN30_TRACKER_KHONG_THROTTLE"


class DieuTietRequest:
    """Dieu tiet nhip goi mang bang cua so truot (sliding window).

    Ghi lai moc thoi gian cac request THAT SU da di ra mang (khong tinh cache
    hit). Truoc moi request moi, neu so request trong `cua_so` giay gan nhat
    da dat `gioi_han`, ngu vua du de moc cu nhat roi khoi cua so roi moi cho
    request tiep tuc.
    """

    def __init__(
        self,
        gioi_han: int = GIOI_HAN_REQUEST_MOI_PHUT,
        cua_so: float = CUA_SO_DIEU_TIET_GIAY,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.gioi_han = gioi_han
        self.cua_so = cua_so
        self.time_fn = time_fn
        self.sleep_fn = sleep_fn
        self._moc_thoi_gian: list[float] = []

    def _loai_moc_qua_cu(self, now: float) -> None:
        self._moc_thoi_gian = [t for t in self._moc_thoi_gian if now - t < self.cua_so]

    def cho_phep(self) -> None:
        """Goi truoc MOI request that ra mang. Co the ngu ben trong ham nay."""
        if os.environ.get(ENV_TAT_THROTTLE) == "1":
            return
        now = self.time_fn()
        self._loai_moc_qua_cu(now)
        if len(self._moc_thoi_gian) >= self.gioi_han:
            moc_cu_nhat = self._moc_thoi_gian[0]
            thoi_gian_ngu = self.cua_so - (now - moc_cu_nhat)
            if thoi_gian_ngu > 0:
                logger.info(
                    "Đã đạt %d request/%.0fs, tạm ngủ %.1f giây để tránh vnstock "
                    "thoát tiến trình do vượt giới hạn tốc độ (không phải bị treo)",
                    self.gioi_han, self.cua_so, thoi_gian_ngu,
                )
                self.sleep_fn(thoi_gian_ngu)
                now = self.time_fn()
                self._loai_moc_qua_cu(now)
        self._moc_thoi_gian.append(now)


# Doi tuong dieu tiet dung chung cho ca file - moi lan chay build.py la 1 tien
# trinh, dung chung 1 cua so truot cho tat ca lenh goi mang trong tien trinh do.
_throttle = DieuTietRequest()


def cached(fn: Callable[[], Any], key: str, cache_dir: Path = CACHE_DIR) -> Any:
    """Cache ket qua JSON-serializable cua fn() theo khoa `key`, tach theo ngay."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / f"{key}-{date.today().isoformat()}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    kq = fn()
    p.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
    return kq


def _mo_ta_danh_sach_ma(symbols: list[str]) -> str:
    """Mo ta ngan gon 1 danh sach ma de dua vao log (day du neu it, tom tat neu dai)."""
    if len(symbols) <= 10:
        return ", ".join(symbols)
    return f"{len(symbols)} mã ({', '.join(symbols[:3])}, ..., {', '.join(symbols[-3:])})"


def chuan_hoa_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """Giu dung 3 cot can, bo phien khong khop lenh (volume = 0)."""
    for cot in COT_CAN:
        if cot not in raw.columns:
            raise ValueError(f"Thiếu cột '{cot}' trong dữ liệu OHLCV")
    df = raw[list(COT_CAN)].copy()
    df["time"] = pd.to_datetime(df["time"])
    so_dong_truoc = len(df)
    df = df[df["volume"] > 0]
    so_bi_loai = so_dong_truoc - len(df)
    if so_bi_loai > 0:
        logger.warning("Loại %d phiên không khớp lệnh (volume = 0)", so_bi_loai)
    return df.reset_index(drop=True)


def _df_to_cache(df: pd.DataFrame) -> dict:
    """Tuan tu hoa DataFrame OHLCV sang dang JSON (time -> chuoi ISO)."""
    d = df.copy()
    d["time"] = d["time"].astype(str)
    return {"records": d.to_dict(orient="records")}


def _df_from_cache(payload: dict) -> pd.DataFrame:
    """Dung lai DataFrame tu cache, dam bao dtype giong het khi lay truc tiep."""
    df = pd.DataFrame(payload["records"])
    if df.empty:
        df = pd.DataFrame(columns=list(COT_CAN))
    df["time"] = pd.to_datetime(df["time"])
    df["close"] = pd.to_numeric(df["close"])
    df["volume"] = pd.to_numeric(df["volume"])
    return df[list(COT_CAN)]


def fetch_hose_universe() -> list[str]:
    """Toan bo co phieu niem yet HOSE (bo ETF, chung quyen, trai phieu). Co cache."""

    def goi_that() -> list[str]:
        from vnstock import Listing

        _throttle.cho_phep()
        df = Listing().symbols_by_exchange()
        hose = df[
            df["exchange"].astype(str).str.upper().isin(HOSE_EXCHANGES)
            & (df["type"].astype(str).str.lower() == "stock")
        ]
        return sorted(hose["symbol"].astype(str).str.upper().unique().tolist())

    return cached(goi_that, "hose-universe", CACHE_DIR)


def fetch_daily(symbol: str, start: date, end: date) -> pd.DataFrame:
    """OHLCV ngay. Tra DataFrame rong neu ma khong co du lieu. Co cache."""
    key = f"daily-{symbol}-{start.isoformat()}-{end.isoformat()}"

    def goi_that() -> dict:
        from vnstock import Quote

        _throttle.cho_phep()
        try:
            raw = Quote(symbol=symbol, source=VNSTOCK_SOURCE).history(
                start=start.isoformat(), end=end.isoformat(), interval="1D"
            )
        except Exception as e:
            logger.warning("Không lấy được lịch sử giá %s: %s", symbol, e)
            raw = None
        if raw is None or raw.empty:
            df = pd.DataFrame(columns=list(COT_CAN))
        else:
            df = chuan_hoa_daily(raw)
        return _df_to_cache(df)

    payload = cached(goi_that, key, CACHE_DIR)
    return _df_from_cache(payload)


def fetch_daily_batch(
    symbols: list[str],
    start: date,
    end: date,
    nguong_loi: float = 0.3,
    fetch_fn: Callable[[str, date, date], pd.DataFrame] = fetch_daily,
) -> dict[str, pd.DataFrame]:
    """Lay gia OHLCV cho ca danh sach ma.

    Phan biet "1 vai ma khong co du lieu" (binh thuong) voi "mat mang/API sap"
    (bat thuong): neu ty le ma tra ve rong vuot `nguong_loi`, nem RuntimeError
    thay vi de bo quy tac hieu nham la "khong co giao dich".
    """
    ket_qua: dict[str, pd.DataFrame] = {}
    ma_loi: list[str] = []
    for sym in symbols:
        df = fetch_fn(sym, start, end)
        if df is None or df.empty:
            ma_loi.append(sym)
        else:
            ket_qua[sym] = df

    ty_le_loi = len(ma_loi) / len(symbols) if symbols else 0.0
    if ty_le_loi > nguong_loi:
        raise RuntimeError(
            f"Tỷ lệ mã lỗi ({len(ma_loi)}/{len(symbols)} = {ty_le_loi:.0%}) vượt "
            f"ngưỡng {nguong_loi:.0%} — nghi ngờ lỗi hạ tầng (mất mạng/API sập), "
            f"không tiếp tục để tránh hiểu nhầm là không có giao dịch."
        )
    if ma_loi:
        logger.warning("Không lấy được giá cho %d mã: %s", len(ma_loi), _mo_ta_danh_sach_ma(ma_loi))
        for sym in symbols:
            if sym in ma_loi:
                ket_qua.setdefault(sym, pd.DataFrame(columns=list(COT_CAN)))
    return ket_qua


def fetch_shares_outstanding(symbols: list[str]) -> dict[str, int]:
    """SLCP luu hanh qua price_board (Company.overview() da vo o vnstock 3.5.1).

    Goi theo lo BATCH_SIZE_SHARES ma de tranh timeout. Co cache theo dau vet
    (hash) cua danh sach ma da sap xep, khong phu thuoc thu tu truyen vao.
    """
    ma_sap_xep = sorted(set(s.strip().upper() for s in symbols))
    dau_vet = hashlib.md5(",".join(ma_sap_xep).encode("utf-8")).hexdigest()[:12]
    key = f"shares-outstanding-{len(ma_sap_xep)}ma-{dau_vet}"

    def goi_that() -> dict[str, int]:
        from vnstock import Trading

        out: dict[str, int] = {}
        for i in range(0, len(symbols), BATCH_SIZE_SHARES):
            lo = symbols[i:i + BATCH_SIZE_SHARES]
            _throttle.cho_phep()
            try:
                df = Trading(source=VNSTOCK_SOURCE.lower(), show_log=False).price_board(symbols_list=lo)
            except Exception as e:
                logger.warning(
                    "price_board lỗi ở lô mã %s: %s", _mo_ta_danh_sach_ma(lo), e
                )
                continue
            if df is None or df.empty:
                continue
            df.columns = [f"{c[0]}_{c[1]}" if isinstance(c, tuple) else str(c) for c in df.columns]
            if "listing_symbol" not in df.columns or "listing_listed_share" not in df.columns:
                logger.warning("price_board thiếu cột listing_symbol/listing_listed_share")
                continue
            for _, row in df.iterrows():
                sym = str(row.get("listing_symbol", "")).strip().upper()
                try:
                    val = int(row.get("listing_listed_share", 0) or 0)
                except (TypeError, ValueError):
                    logger.warning("Bỏ mã %s: giá trị SLCP không parse được", sym)
                    continue
                if not sym:
                    continue
                if val > 0:
                    out[sym] = val
                else:
                    logger.warning("Bỏ mã %s: SLCP <= 0", sym)

        ma_thieu = sorted(set(s.strip().upper() for s in symbols) - set(out.keys()))
        if ma_thieu:
            logger.warning(
                "Không có kết quả SLCP cho %s trong tổng %d mã đầu vào",
                _mo_ta_danh_sach_ma(ma_thieu), len(symbols),
            )
        return out

    return cached(goi_that, key, CACHE_DIR)
