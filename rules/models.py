"""Kieu du lieu dung chung cho bo may quy tac. Khong co I/O o day."""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd


@dataclass
class StockInput:
    """Toan bo thong tin ve mot ma can de chay quy tac.

    daily: DataFrame co cot 'time' (datetime64), 'close' (nghin dong - giu nguyen don vi tu vnstock),
    'volume' (co phieu). TRONG CLOSE: luon la don vi nghin dong nhu trai tu vnstock; moi phep tinh
    tien phai nhan PRICE_UNIT_VND tu rules.definitions de ra VND; tuyet doi KHONG so sanh truc tiep
    'close' voi cac nguong VND trong thresholds.yaml.
    free_float: None nghia la THIEU DU LIEU, khong duoc doan.
    listing_date: None nghia la CHUA XAC NHAN ngay niem yet (mã không có trong
    data/manual.yaml) - TUYET DOI khong duoc hieu la "niem yet tu rat lau roi".
    Truoc day co bug mac dinh date(1900,1,1) khien he thong bia ra "Da niem yet
    1500+ thang" cho ma chua co du lieu - da fix, gio phai de None va bao thieu.
    """
    symbol: str
    daily: pd.DataFrame
    shares_outstanding: int
    listing_date: Optional[date] = None
    free_float: Optional[float] = None
    in_previous_basket: bool = False
    warning_status: str = "none"        # none|warning|control|restricted|suspended
    lnst_positive: Optional[bool] = None
    audit_opinion: str = "unknown"      # unqualified|qualified|unknown


@dataclass
class ScreenResult:
    """Ket qua mot buoc sang loc cho mot ma."""
    symbol: str
    step: str            # vd "free_float"
    rule_ref: str        # vd "3.3.3"
    passed: bool
    message: str         # cau tieng Viet giai thich, hien thang len web
    shortfall: Optional[float] = None   # con thieu bao nhieu (don vi cua chinh tieu chi)


@dataclass
class BasketResult:
    """Ket qua chay toan bo quy trinh."""
    constituents: list[str] = field(default_factory=list)
    reserve: list[str] = field(default_factory=list)
    metrics: dict[str, dict] = field(default_factory=dict)      # symbol -> so lieu tinh duoc
    screens: dict[str, list[ScreenResult]] = field(default_factory=dict)  # symbol -> cac buoc
    missing_data: list[str] = field(default_factory=list)       # ma thieu free float/LNST
    canh_bao: list[str] = field(default_factory=list)           # canh bao chung (vd ro thieu ma)
