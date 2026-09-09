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
    listing_date: None nghia la CHUA XAC NHAN mot ngay niem yet CU THE - TUYET DOI
    khong duoc hieu la "niem yet tu rat lau roi". Truoc day co bug mac dinh
    date(1900,1,1) khien he thong bia ra "Da niem yet 1500+ thang" cho ma chua co
    du lieu - da fix, gio phai de None va bao thieu.
    listing_date co the den tu 2 nguon: (1) xac nhan thu cong trong data/manual.yaml
    (uu tien cao nhat), hoac (2) suy tu ngay giao dich dau tien trong chuoi gia khi
    ma do ro rang moi niem yet trong cua so du lieu (xem build.py, niem_yet_nguon
    = "suy từ ngày giao dịch đầu tiên"). Khong duoc bia mot ngay cu the cho truong
    hop ma da giao dich tu TRUOC cua so du lieu - dung co niem_yet_truoc_cua_so.
    niem_yet_truoc_cua_so: True nghia la chuoi gia bat dau sat/truoc ngay bat dau
    cua so yeu cau -> suy ra ma da niem yet it nhat bang do dai cua so (vd 12 thang),
    du KHONG biet ngay niem yet chinh xac. Khac voi listing_date=None+False (chua
    xac nhan duoc gi ca) - truong hop nay la CO bang chung (da giao dich) nhung
    khong co ngay cu the, nen duoc coi la dat dieu kien 6 thang o screen_eligibility.
    """
    symbol: str
    daily: pd.DataFrame
    shares_outstanding: int
    listing_date: Optional[date] = None
    niem_yet_truoc_cua_so: bool = False
    free_float: Optional[float] = None
    in_previous_basket: bool = False
    warning_status: str = "none"        # none|warning|control|restricted|suspended
    lnst_positive: Optional[bool] = None
    audit_opinion: str = "unknown"      # unqualified|qualified|unknown
    # 3 truong hien thi (khong dung trong logic sang loc) de web tu kiem tra duoc
    # nguon LNST: tu dong (vnstock) hay xac nhan thu cong (manual.yaml de) thang.
    lnst_ty: Optional[float] = None      # LNST quy ra ty dong
    lnst_ky: Optional[str] = None        # nhan ky bao cao, vd "Năm 2025"
    lnst_nguon: Optional[str] = None     # "tự động" | "xác nhận thủ công"
    # Nguon cua listing_date/niem_yet_truoc_cua_so, hien thi de nguoi doc web tu
    # kiem tra can cu: "xác nhận thủ công" | "suy từ ngày giao dịch đầu tiên" |
    # "giao dịch từ trước cửa sổ dữ liệu" | None (khong biet gi ca)
    niem_yet_nguon: Optional[str] = None
    # Tuyen kiem tra cheo voi cong bo VNAllshare chinh thuc cua HOSE (xem build.py,
    # lap_stock_inputs): True khi ma DAT dieu kien tham gia CHI nho suy luan
    # "giao dich tu truoc cua so" (niem_yet_nguon == "giao dịch từ trước cửa sổ dữ
    # liệu", KHONG co listing_date xac nhan thu cong) NHUNG lai KHONG co mat trong
    # danh muc VNAllshare cua cong bo HOSE ky gan nhat - dau hieu ma co the vua
    # chuyen san (vd UPCoM -> HOSE, xem ca MCH) hoac chua du dieu kien, can nguoi
    # xac nhan lai listing_date thu cong. KHONG tu dong loai ma, chi canh bao.
    canh_bao_chuyen_san: bool = False


@dataclass
class ScreenResult:
    """Ket qua mot buoc sang loc cho mot ma."""
    symbol: str
    step: str            # vd "free_float"
    rule_ref: str        # vd "3.3.3"
    passed: bool
    message: str         # cau tieng Viet giai thich, hien thang len web
    shortfall: Optional[float] = None   # con thieu bao nhieu (don vi cua chinh tieu chi)
    # True nghia la buoc nay TRUOT vi THIEU DU LIEU DAU VAO (free float/ngay niem
    # yet/LNST chua co, hoac khong tinh duoc turnover do thieu free float) - KHONG
    # phai vi ma khong dat tieu chi THUC CHAT. Web dung truong nay de tach nhom
    # "chua ket luan duoc (thieu du lieu)" khoi nhom "nguy co bi loai" (that su
    # truot tieu chi), THAY VI do chuoi tieng Viet trong message (de vo).
    thieu_du_lieu: bool = False


@dataclass
class BasketResult:
    """Ket qua chay toan bo quy trinh."""
    constituents: list[str] = field(default_factory=list)
    reserve: list[str] = field(default_factory=list)
    metrics: dict[str, dict] = field(default_factory=dict)      # symbol -> so lieu tinh duoc
    screens: dict[str, list[ScreenResult]] = field(default_factory=dict)  # symbol -> cac buoc
    missing_data: list[str] = field(default_factory=list)       # ma thieu free float/LNST
    canh_bao: list[str] = field(default_factory=list)           # canh bao chung (vd ro thieu ma)
