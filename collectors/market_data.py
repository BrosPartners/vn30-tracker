"""Adapter vnstock - tang duy nhat cham mang.

Cache theo NGAY: file .cache/<key>-<YYYY-MM-DD>.json. Chay lai trong ngay thi
khong goi mang, sang hom sau tu dong lay moi. Moi ham fetch tu sinh khoa cache
tu day du tham so cua no, nguoi goi khong phai nghi ve khoa.

Rieng du lieu QUA KHU DA CHOT (vi du cua so gia ket thuc truoc hom nay) khong
bao gio doi nua - cache cho loai nay la BAT BIEN, luu o .cache/lichsu/<key>.json
(khong gan ngay, khong bao gio het han). Xem ham cached() va fetch_daily().
"""
import hashlib
import json
import logging
import os
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
import tenacity as _tenacity

logger = logging.getLogger(__name__)

# --- Tat retry NGAM cua vnstock (nguyen nhan #2 gay chet vi RateLimitExceeded) ---
# Moi ham cham mang cua vnstock (Quote.history, Finance.income_statement,
# Listing.symbols_by_exchange, Trading.price_board) duoc tu ban vnstock trang
# tri bang @retry cua thu vien tenacity (Config.RETRIES=3, backoff mu). Retry
# nay nam BEN TRONG vnstock, SAU luot kiem tra dieu tiet noi bo cua no (vnai) -
# nghia la 1 lan goi "hop le" ve phia _throttle cua repo nay co the am tham phat
# sinh toi 3 request THAT ra mang khi backend tra loi loi, nhung _throttle chi
# dem duoc 1. Day chinh la duong request "lot luoi" gay chet o giay thu 70 du da
# ha throttle xuong 25/phut.
#
# @retry cua vnstock "dong bang" gia tri Config.RETRIES ngay LUC MODULE
# vnstock.api.* duoc import (vi no la tham so truyen vao decorator luc dinh
# nghia ham, khong doc lai moi lan goi) - nen sua Config.RETRIES SAU KHI import
# se khong co tac dung. Cach duy nhat kiem soat duoc la thay the ham
# `tenacity.retry` NGAY TU DAY, TRUOC KHI vnstock duoc import lan dau (import
# vnstock luon la lazy, o trong than cac ham goi_that() ben duoi) - collectors/
# la tang duy nhat cham mang nen day chac chan la noi vnstock duoc cham toi dau
# tien trong toan bo tien trinh.
_retry_goc_cua_tenacity = _tenacity.retry  # giu lai ham goc TRUOC KHI thay the, tranh de quy


def _tat_retry_ngam_cua_vnstock(*args, **kwargs):
    """Thay ham tenacity.retry() ma vnstock dung: luon chi thu DUNG 1 lan.

    Nho vay moi request that ra mang tuong ung dung 1 lan goi _throttle.cho_phep()
    truoc do - dem dung, khong con request nao "lot luoi" qua retry ngam.
    """
    return _retry_goc_cua_tenacity(stop=_tenacity.stop_after_attempt(1))


_tenacity.retry = _tat_retry_ngam_cua_vnstock

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
#
# Tren runner GitHub Actions, goi "Khach" cua vnstock chi cho ~20 request/phut
# (thap hon nhieu so voi may local) - vi vay cho phep chinh qua bien moi
# truong VN30_TRACKER_GIOI_HAN_REQUEST, mac dinh giu 55 khi khong set.
ENV_GIOI_HAN_REQUEST = "VN30_TRACKER_GIOI_HAN_REQUEST"


def _doc_gioi_han_request_tu_env(mac_dinh: int = 55) -> int:
    """Doc gioi han request/phut tu bien moi truong, roi ve mac dinh neu khong set/khong hop le."""
    gia_tri = os.environ.get(ENV_GIOI_HAN_REQUEST)
    if gia_tri is None:
        return mac_dinh
    try:
        return int(gia_tri)
    except ValueError:
        logger.warning(
            "Giá trị %s=%r không phải số nguyên hợp lệ, dùng mặc định %d",
            ENV_GIOI_HAN_REQUEST, gia_tri, mac_dinh,
        )
        return mac_dinh


GIOI_HAN_REQUEST_MOI_PHUT = _doc_gioi_han_request_tu_env()
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


THU_MUC_LICH_SU = "lichsu"  # thu muc con chua cache BAT BIEN (khong gan ngay)


def cached(
    fn: Callable[[], Any],
    key: str,
    cache_dir: Path = CACHE_DIR,
    bat_bien: bool = False,
) -> Any:
    """Cache ket qua JSON-serializable cua fn() theo khoa `key`.

    Mac dinh (bat_bien=False) cache tach theo NGAY nhu truoc gio: file
    <key>-<hom nay>.json, sang hom sau tu dong lay lai (dung cho du lieu con
    co the doi, vi du gia trong ngay hom nay).

    Khi bat_bien=True (du lieu QUA KHU da chot, khong bao gio doi nua) thi
    dung file <key>.json trong thu muc con rieng (khong gan ngay) va KHONG
    BAO GIO het han - tranh phai tai lai toan bo vu tru moi ngay chi vi doi
    ngay he thong, trong khi ban than du lieu khong doi.
    """
    if bat_bien:
        thu_muc = cache_dir / THU_MUC_LICH_SU
        thu_muc.mkdir(parents=True, exist_ok=True)
        p = thu_muc / f"{key}.json"
    else:
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
    """OHLCV ngay. Tra DataFrame rong neu ma khong co du lieu. Co cache.

    Neu `end` truoc hom nay: cua so gia da CHOT (khong con phien nao moi phat
    sinh trong khoang [start, end] nua) -> dung cache BAT BIEN, khong het han.
    Neu `end` la hom nay hoac tuong lai: cua so con "song" (hom nay co the
    them phien moi khi thi truong dang giao dich) -> giu cache theo ngay nhu cu.
    """
    key = f"daily-{symbol}-{start.isoformat()}-{end.isoformat()}"
    bat_bien = end < date.today()

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

    payload = cached(goi_that, key, CACHE_DIR, bat_bien=bat_bien)
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


def fetch_current_market_cap(symbols: list[str]) -> dict[str, float]:
    """Von hoa HIEN TAI (VND) qua price_board - dung de sang thu, xep hang toan bo
    HOSE bang 1 luot goi RE (theo lo BATCH_SIZE_SHARES ma), truoc khi quyet dinh
    ma nao dang lay lich su gia 12 thang (goi API ton kem hon nhieu).

    Gia lay tu match_match_price (gia khop lenh gan nhat, don vi VND/co phieu -
    KHAC voi 'close' cua Quote().history() la nghin dong). Neu ma chua co lenh
    khop trong phien (0 hoac thieu), roi ve listing_ref_price (gia tham chieu) de
    khong bo sot ma khoi buoc sang thu chi vi chua giao dich trong ngay.

    Day la sang thu RIENG, khong lien quan gtvh() (binh quan 12 thang) dung de xep
    hang chinh thuc trong rules/ - ham nay chi de chon vu tru con truoc.
    """
    ma_sap_xep = sorted(set(s.strip().upper() for s in symbols))
    dau_vet = hashlib.md5(",".join(ma_sap_xep).encode("utf-8")).hexdigest()[:12]
    key = f"current-market-cap-{len(ma_sap_xep)}ma-{dau_vet}"

    def goi_that() -> dict[str, float]:
        from vnstock import Trading

        out: dict[str, float] = {}
        for i in range(0, len(symbols), BATCH_SIZE_SHARES):
            lo = symbols[i:i + BATCH_SIZE_SHARES]
            _throttle.cho_phep()
            try:
                df = Trading(source=VNSTOCK_SOURCE.lower(), show_log=False).price_board(symbols_list=lo)
            except Exception as e:
                logger.warning(
                    "price_board lỗi ở lô mã %s (vốn hóa hiện tại): %s", _mo_ta_danh_sach_ma(lo), e
                )
                continue
            if df is None or df.empty:
                continue
            df.columns = [f"{c[0]}_{c[1]}" if isinstance(c, tuple) else str(c) for c in df.columns]
            can = ("listing_symbol", "listing_listed_share", "match_match_price")
            if not all(c in df.columns for c in can):
                logger.warning("price_board thiếu cột cần cho vốn hóa hiện tại (%s)", ", ".join(can))
                continue
            co_ref = "listing_ref_price" in df.columns
            for _, row in df.iterrows():
                sym = str(row.get("listing_symbol", "")).strip().upper()
                if not sym:
                    continue
                try:
                    slcp = int(row.get("listing_listed_share", 0) or 0)
                except (TypeError, ValueError):
                    continue
                try:
                    gia = float(row.get("match_match_price", 0) or 0)
                except (TypeError, ValueError):
                    gia = 0.0
                if gia <= 0 and co_ref:
                    try:
                        gia = float(row.get("listing_ref_price", 0) or 0)
                    except (TypeError, ValueError):
                        gia = 0.0
                if slcp > 0 and gia > 0:
                    out[sym] = slcp * gia
                else:
                    logger.warning("Bỏ mã %s: thiếu SLCP hoặc giá để tính vốn hóa hiện tại", sym)

        ma_thieu = sorted(set(s.strip().upper() for s in symbols) - set(out.keys()))
        if ma_thieu:
            logger.warning(
                "Không tính được vốn hóa hiện tại cho %s trong tổng %d mã đầu vào",
                _mo_ta_danh_sach_ma(ma_thieu), len(symbols),
            )
        return out

    return cached(goi_that, key, CACHE_DIR)


# ---------------------------------------------------------------------------
# LNST cua dong cong ty me (Dieu 3.1) - dung cho sang loc loi nhuan 4.3.1.d
# ---------------------------------------------------------------------------

CHI_TIEU_LNST_CTY_ME = "attributable_to_parent_company"


def _lay_dong_lnst(df: Optional[pd.DataFrame], cot: str) -> Optional[float]:
    """Boc gia tri chi tieu LNST cua dong cong ty me tai 1 cot (nam hoac quy).

    Tra None neu thieu cot, thieu dong chi tieu, hoac gia tri khong doc duoc so -
    KHONG DUOC DOAN (vd tra 0).
    """
    if df is None or df.empty or "item_id" not in df.columns or cot not in df.columns:
        return None
    dong = df[df["item_id"] == CHI_TIEU_LNST_CTY_ME]
    if dong.empty:
        return None
    try:
        return float(dong.iloc[0][cot])
    except (TypeError, ValueError):
        return None


def _cot_quy(nam: int, quy: int) -> str:
    """Ten cot ky quy trong DataFrame income_statement(period='quarter') cua vnstock."""
    return f"{nam}-Q{quy}"


def fetch_lnst(symbol: str, as_of: Optional[date] = None) -> Optional[dict]:
    """LNST cua dong cong ty me tai ky bao cao gan nhat (Dieu 3.1).

    Uu tien ban nien nam hien tai (cong tu 2 bao cao quy Q1+Q2, vi vnstock khong co
    ban soat xet ban nien rieng) - neu chua du 2 quy thi roi ve nam gan nhat (cot dau
    tien cua DataFrame nam, vnstock tra giam dan theo nam). Neu ca hai deu khong lay
    duoc (thieu chi tieu, loi mang, mã khong co BCTC) thi tra None - KHONG DUOC DOAN.
    """
    as_of = as_of or date.today()
    nam_hien_tai = as_of.year
    key = f"lnst-{symbol}"

    def goi_that() -> Optional[dict]:
        from vnstock import Finance

        # --- Uu tien: ban nien = Q1 + Q2 nam hien tai, tu bao cao quy ---
        _throttle.cho_phep()
        try:
            df_quy = Finance(symbol=symbol, source=VNSTOCK_SOURCE).income_statement(
                period="quarter", lang="vi")
        except Exception as e:
            logger.warning("Không lấy được BCTC quý %s: %s", symbol, e)
            df_quy = None

        q1 = _lay_dong_lnst(df_quy, _cot_quy(nam_hien_tai, 1))
        q2 = _lay_dong_lnst(df_quy, _cot_quy(nam_hien_tai, 2))
        if q1 is not None and q2 is not None:
            return {
                "lnst_vnd": q1 + q2,
                "ky": f"Bán niên {nam_hien_tai} (cộng từ báo cáo quý 1+2, "
                      f"không phải bản soát xét bán niên chính thức)",
                "nguon": "vnstock BCTC quý (Q1+Q2), attributable_to_parent_company",
            }

        # --- Roi ve: nam gan nhat, tu bao cao nam ---
        _throttle.cho_phep()
        try:
            df_nam = Finance(symbol=symbol, source=VNSTOCK_SOURCE).income_statement(
                period="year", lang="vi")
        except Exception as e:
            logger.warning("Không lấy được BCTC năm %s: %s", symbol, e)
            df_nam = None

        if df_nam is None or df_nam.empty or "item_id" not in df_nam.columns:
            return None
        cot_nam = [c for c in df_nam.columns if c not in ("item", "item_en", "item_id")]
        if not cot_nam:
            return None
        cot_moi_nhat = cot_nam[0]  # vnstock tra cot giam dan theo nam, cot dau la moi nhat
        gia_tri = _lay_dong_lnst(df_nam, cot_moi_nhat)
        if gia_tri is None:
            return None
        return {
            "lnst_vnd": gia_tri,
            "ky": f"Năm {cot_moi_nhat}",
            "nguon": "vnstock BCTC năm, attributable_to_parent_company",
        }

    return cached(goi_that, key, CACHE_DIR)


def fetch_lnst_batch(
    symbols: list[str],
    nguong_loi: float = 0.5,
    fetch_fn: Callable[[str], Optional[dict]] = fetch_lnst,
) -> dict[str, dict]:
    """Lay LNST cho ca danh sach ma (thuong la top N theo GTVH, khong phai toan vu tru).

    Nguong loi mac dinh cao hon fetch_daily_batch (0.5 vs 0.3) vi nhieu ma nho tren
    HOSE von di khong co BCTC day du bang vnstock, ty le thieu tu nhien da cao hon
    la dau hieu ha tang sap.
    """
    ket_qua: dict[str, dict] = {}
    ma_loi: list[str] = []
    for sym in symbols:
        kq = fetch_fn(sym)
        if kq is None:
            ma_loi.append(sym)
        else:
            ket_qua[sym] = kq

    ty_le_loi = len(ma_loi) / len(symbols) if symbols else 0.0
    if ty_le_loi > nguong_loi:
        raise RuntimeError(
            f"Tỷ lệ mã lỗi LNST ({len(ma_loi)}/{len(symbols)} = {ty_le_loi:.0%}) vượt "
            f"ngưỡng {nguong_loi:.0%} — nghi ngờ lỗi hạ tầng (mất mạng/API sập), "
            f"không tiếp tục để tránh hiểu nhầm là không có dữ liệu LNST."
        )
    if ma_loi:
        logger.warning("Không lấy được LNST cho %d mã: %s", len(ma_loi), _mo_ta_danh_sach_ma(ma_loi))
    return ket_qua
