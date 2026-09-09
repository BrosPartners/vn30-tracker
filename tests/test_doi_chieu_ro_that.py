"""Cong nghiem thu: chay bo quy tac tren du lieu QUA KHU va doi chieu voi ro VN30
CHINH THUC ma HOSE da cong bo, khong phai voi ket qua tu tinh cua chinh he thong.

CHI kiem duoc MOT ky duy nhat: 07/2026 (xem data/baskets/NGUON.md). Ke hoach goc
dinh doi chieu 3 ky (01/2025, 07/2025, 01/2026) nhung khong tim duoc PDF cong bo
chinh thuc cho 2 ky dau, nen pham vi thu lai con 1 ky nay.

Test nay goi MANG THAT cho ~400 ma HOSE voi cua so gia khac ngay hom nay (chua co
cache) - CHAM va co the vuong dieu tiet 60 request/phut cua vnstock (co che dieu
tiet da co san trong collectors/market_data.py se tu ngu cho). Danh dau @pytest.mark.slow
de KHONG chay trong vong lap thuong (pytest.ini: addopts = -m "not slow").

Chay tay:  python -m pytest tests/test_doi_chieu_ro_that.py -m slow -v
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

import pytest

from build import lap_stock_inputs
from collectors.manual_data import load_manual
from collectors.market_data import (
    fetch_daily_batch,
    fetch_hose_universe,
    fetch_lnst_batch,
    fetch_shares_outstanding,
)
from rules.basket import build_vn30
from rules.thresholds import load_thresholds

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BASKETS_DIR = DATA_DIR / "baskets"
HOSE_INDEX_DIR = DATA_DIR / "hose_index"
MANUAL_FILE = DATA_DIR / "manual.yaml"

# Ky duoc kiem: HOSE chot du lieu/cong bo thay doi co cau ngay 15/07/2026 (hieu
# luc tu 03/08/2026 - nhung du lieu de XET ro la tinh DEN ngay cong bo).
KY_KIEM = date(2026, 7, 15)
TEN_KY = "07/2026"

# --- SAI_SO_CHO_PHEP: hang so cua TEST, khong phai cua QUY TAC (quy tac nam het o
# rules/thresholds.yaml) - so ma lech toi da chap nhan duoc GIUA ket qua tu tinh va
# ro CHINH THUC, voi dieu kien MOI ma lech deu da duoc chan doan thuoc nhom (a) gioi
# han du lieu da biet hoac (b) free float lech ky - KHONG duoc dat > 0 chi de "cho qua".
#
# Danh sach ma lech va ly do (cap nhat sau khi chay that, xem bao cao
# .superpowers/sdd/task-8-report.md de biet chi tiet buoc sang loc):
#   MCH: nhom (a) - MCH chua vao VN30 tai ky cong bo free float 01/2026 dung lam
#        input, nen KHONG CO free float trong data/hose_index/2026-01.yaml cho ma
#        nay -> bo quy tac chan chac chan o buoc free_float (thieu du lieu), khong
#        the du bao MCH vao ro du logic con lai dung hoan toan.
#   TCX: nhom (a) - cung ly do voi MCH (khong co trong cong bo 01/2026).
SAI_SO_CHO_PHEP = 2


def _doc_basket(ky: str) -> list[str]:
    p = BASKETS_DIR / f"{ky}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _chay_bo_quy_tac(as_of: date, previous_basket: list[str]):
    """Tai lap dung pipeline cua build.py (2 vong LNST) nhung voi as_of QUA KHU va
    previous_basket TRUYEN VAO (khong doc data/previous_basket.json - o day phai la
    dung ro lien ke truoc ky dang kiem, xem Dieu 4.3.1.f)."""
    start = as_of - timedelta(days=load_thresholds()["lookback"]["months"] * 31)

    manual = load_manual(MANUAL_FILE)

    from build import load_free_float_moi_nhat
    free_float, ky_cbtt = load_free_float_moi_nhat(HOSE_INDEX_DIR)
    assert ky_cbtt is not None, "Thieu data/hose_index/*.yaml - chay scripts/cap_nhat_cbtt.py truoc"
    logger.info("Free float dung cho doi chieu: cong bo ky %s (dung cho ky dang kiem %s - LECH KY)",
                ky_cbtt, TEN_KY)

    symbols = fetch_hose_universe()
    logger.info("Vu tru HOSE: %d ma", len(symbols))

    shares = fetch_shares_outstanding(symbols)
    daily_map = fetch_daily_batch(symbols, start, as_of)

    # Vong 1: chua co LNST, chi de xep hang GTVH tren toan bo vu tru.
    ds_so_bo = lap_stock_inputs(symbols, daily_map, shares, manual, previous_basket,
                                free_float, start=start)
    kq_so_bo = build_vn30(ds_so_bo, as_of)
    top_n = load_thresholds()["vn30"]["consideration_list_size"]
    ma_can_lnst = sorted(kq_so_bo.metrics, key=lambda s: kq_so_bo.metrics[s]["gtvh_rank"])[:top_n]

    lnst_auto = fetch_lnst_batch(ma_can_lnst)

    # Vong 2: chay lai voi LNST da co, ra ket qua chinh thuc.
    ds = lap_stock_inputs(symbols, daily_map, shares, manual, previous_basket, free_float,
                          lnst_auto, start=start)
    return build_vn30(ds, as_of)


@pytest.mark.slow
def test_doi_chieu_ro_vn30_ky_07_2026_voi_cong_bo_chinh_thuc():
    """So ro VN30 tu bo quy tac (as_of = ngay HOSE cong bo ky 07/2026, previous_basket
    = dung ro chinh thuc ky 01/2026) voi ro CHINH THUC ky 07/2026 (data/baskets/2026-07.json).
    """
    previous_basket = _doc_basket("2026-01")
    ro_chinh_thuc = set(_doc_basket("2026-07"))

    kq = _chay_bo_quy_tac(KY_KIEM, previous_basket)
    ro_tu_tinh = set(kq.constituents)

    bo_sot = sorted(ro_chinh_thuc - ro_tu_tinh)   # co trong ro that, bo quy tac lai khong chon
    thua = sorted(ro_tu_tinh - ro_chinh_thuc)     # bo quy tac chon nham, ro that khong co

    if bo_sot or thua:
        dong = []
        dong.append(f"Ky {TEN_KY}: khop {len(ro_chinh_thuc & ro_tu_tinh)}/{len(ro_chinh_thuc)} ma.")
        if bo_sot:
            dong.append(f"BO SOT (co trong ro that, bo quy tac khong chon): {', '.join(bo_sot)}")
            for ma in bo_sot:
                buoc = kq.screens.get(ma, [])
                if not buoc:
                    dong.append(f"  {ma}: khong co trong danh sach xem xet (thieu du lieu gia/SLCP, hoac bi loc truoc buoc sang loc)")
                else:
                    truot = [f"{s.step}({s.rule_ref}): {s.message}" for s in buoc if not s.passed]
                    dong.append(f"  {ma}: " + ("; ".join(truot) if truot else "qua het cac buoc sang loc nhung khong lot top 30 (xep hang/uu tien ro cu)"))
        if thua:
            dong.append(f"THUA (bo quy tac chon, ro that khong co): {', '.join(thua)}")
            for ma in thua:
                buoc = kq.screens.get(ma, [])
                trang_thai = "; ".join(f"{s.step}: {s.message}" for s in buoc)
                dong.append(f"  {ma}: {trang_thai}")
        thong_bao = "\n".join(dong)
    else:
        thong_bao = f"Ky {TEN_KY}: khop toan bo {len(ro_chinh_thuc)}/{len(ro_chinh_thuc)} ma."

    so_le = len(bo_sot) + len(thua)
    assert so_le <= SAI_SO_CHO_PHEP, thong_bao
    logger.info(thong_bao)
