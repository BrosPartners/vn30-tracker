from rules.thresholds import load_thresholds


def test_nguong_khop_quy_tac_v4():
    """Moi nguong phai dung nguyen van Ground Rules v4.0."""
    t = load_thresholds()
    assert t["free_float"]["min_ratio"] == 0.10
    assert t["free_float"]["exception_gtvh_f_existing_vnd"] == 2_000e9
    assert t["free_float"]["exception_gtvh_f_new_vnd"] == 2_500e9
    assert t["liquidity"]["min_turnover_new"] == 0.0005
    assert t["liquidity"]["min_turnover_existing"] == 0.0004
    assert t["vn30"]["min_klgd_kl_shares"] == 300_000
    assert t["vn30"]["min_gtgd_kl_vnd"] == 30e9
    assert t["vn30"]["auto_include_rank"] == 20
    assert t["vn30"]["conditional_rank_max"] == 40
    assert t["vn30"]["basket_size"] == 30
    assert t["vn30"]["consideration_list_size"] == 50
    assert t["vn30"]["reserve_size"] == 5
    assert t["eligibility"]["min_listing_months"] == 6
    assert t["eligibility"]["top_gtvh_exemption_rank"] == 5
    assert t["eligibility"]["top_gtvh_exemption_months"] == 3


def test_moi_nguong_co_trich_dan_dieu_khoan():
    t = load_thresholds()
    for nhom in ("free_float", "liquidity", "vn30", "eligibility"):
        assert t[nhom]["rule_ref"], f"Nhom {nhom} thieu rule_ref"
