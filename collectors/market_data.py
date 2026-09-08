"""Adapter vnstock - tang duy nhat cham mang.

Cache theo NGAY: file .cache/<key>-<YYYY-MM-DD>.json. Chay lai trong ngay thi
khong goi mang, sang hom sau tu dong lay moi.
"""
import json
import logging
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
COT_CAN = ("time", "close", "volume")


def cached(fn: Callable[[], dict], key: str, cache_dir: Path = CACHE_DIR) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / f"{key}-{date.today().isoformat()}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    kq = fn()
    p.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
    return kq


def chuan_hoa_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """Giu dung 3 cot can, bo phien khong khop lenh (volume = 0)."""
    for cot in COT_CAN:
        if cot not in raw.columns:
            raise ValueError(f"Thiếu cột '{cot}' trong dữ liệu OHLCV")
    df = raw[list(COT_CAN)].copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df[df["volume"] > 0]
    return df.reset_index(drop=True)


def fetch_hose_universe() -> list[str]:
    """Toan bo co phieu niem yet HOSE (bo ETF, chung quyen, trai phieu)."""
    from vnstock import Listing

    df = Listing().symbols_by_exchange()
    hose = df[
        df["exchange"].astype(str).str.upper().isin(["HOSE", "HSX"])
        & (df["type"].astype(str).str.lower() == "stock")
    ]
    return sorted(hose["symbol"].astype(str).str.upper().unique().tolist())


def fetch_daily(symbol: str, start: date, end: date) -> pd.DataFrame:
    """OHLCV ngay. Tra DataFrame rong neu ma khong co du lieu."""
    from vnstock import Quote

    try:
        raw = Quote(symbol=symbol, source="VCI").history(
            start=start.isoformat(), end=end.isoformat(), interval="1D"
        )
    except Exception as e:
        logger.warning("Không lấy được lịch sử giá %s: %s", symbol, e)
        return pd.DataFrame(columns=list(COT_CAN))
    if raw is None or raw.empty:
        return pd.DataFrame(columns=list(COT_CAN))
    return chuan_hoa_daily(raw)


def fetch_shares_outstanding(symbols: list[str]) -> dict[str, int]:
    """SLCP luu hanh qua price_board (Company.overview() da vo o vnstock 3.5.1).

    Goi theo lo 50 ma de tranh timeout.
    """
    from vnstock import Trading

    out: dict[str, int] = {}
    for i in range(0, len(symbols), 50):
        lo = symbols[i:i + 50]
        try:
            df = Trading(source="vci", show_log=False).price_board(symbols_list=lo)
        except Exception as e:
            logger.warning("price_board lỗi ở lô %d: %s", i, e)
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
                continue
            if sym and val > 0:
                out[sym] = val
    return out
