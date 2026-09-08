"""Ghep 7 buoc sang loc thanh mot lan chay hoan chinh (Dieu 4.3.1)."""
from datetime import date

from rules.definitions import gtgd_kl, gtvh, gtvh_f, klgd_kl, round_free_float, turnover_ratio
from rules.models import BasketResult, StockInput
from rules.screens import (
    screen_eligibility,
    screen_free_float,
    screen_liquidity,
    screen_profit,
    screen_vn30_liquidity,
)
from rules.thresholds import load_thresholds


def build_vn30(stocks: list[StockInput], as_of: date) -> BasketResult:
    t = load_thresholds()["vn30"]
    result = BasketResult()

    # --- Tinh so lieu va xep hang GTVH tren TOAN BO vu tru (Dieu 4.3.1.e) ---
    for s in stocks:
        result.metrics[s.symbol] = {
            "gtvh": gtvh(s),
            "gtvh_f": gtvh_f(s),
            "gtgd_kl": gtgd_kl(s),
            "klgd_kl": klgd_kl(s),
            "turnover": turnover_ratio(s),
            "free_float": s.free_float,
            "free_float_rounded": None if s.free_float is None else round_free_float(s.free_float),
            "in_previous_basket": s.in_previous_basket,
            "audit_opinion": s.audit_opinion,
        }
        if s.free_float is None or s.lnst_positive is None:
            result.missing_data.append(s.symbol)

    xep = sorted(stocks, key=lambda s: result.metrics[s.symbol]["gtvh"], reverse=True)
    for hang, s in enumerate(xep, start=1):
        result.metrics[s.symbol]["gtvh_rank"] = hang

    # --- Chay 5 buoc sang loc, ghi lai ly do cho MOI ma ---
    dat = []
    for s in xep:
        m = result.metrics[s.symbol]
        buoc = [
            screen_eligibility(s, as_of, m["gtvh_rank"]),
            screen_free_float(s, m["gtvh_f"]),
            screen_liquidity(s, m["turnover"]),
            screen_vn30_liquidity(s, m["klgd_kl"], m["gtgd_kl"]),
            screen_profit(s),
        ]
        result.screens[s.symbol] = buoc
        if all(b.passed for b in buoc):
            dat.append(s)

    # --- Dieu 4.3.1.f: top 20 vao thang; 21-40 uu tien ma ro cu ---
    trong_vung = dat[: t["conditional_rank_max"]]
    chon = [s.symbol for s in trong_vung[: t["auto_include_rank"]]]
    con_lai = trong_vung[t["auto_include_rank"]:]

    for s in con_lai:                      # uu tien ma da co trong ro ky truoc
        if len(chon) >= t["basket_size"]:
            break
        if s.in_previous_basket:
            chon.append(s.symbol)
    for s in con_lai:                      # roi den ma moi
        if len(chon) >= t["basket_size"]:
            break
        if s.symbol not in chon:
            chon.append(s.symbol)

    result.constituents = chon

    # --- Dieu 4.3.1.g: 5 ma GTVH lon nhat con lai ---
    result.reserve = [s.symbol for s in dat if s.symbol not in chon][: t["reserve_size"]]
    return result
