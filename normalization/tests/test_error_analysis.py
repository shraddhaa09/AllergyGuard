"""Unit tests for the error analysis and uncertainty classification module."""

from normalization.error_analysis import (
    run_case_1_soy_leotain,
    run_case_2_onion_sunflower_oil,
    run_case_3_contains_statement,
    run_case_4_soybean_oil,
    run_case_5_nested_milk,
    run_case_6_oreo_uncertain,
    get_error_category_summary,
)


def test_case_1_soy_leotain_candidate_status():
    res = run_case_1_soy_leotain()
    assert res["case_id"] == "CASE_1_SOY_LEOTAIN"
    assert res["status"] == "OBSERVED"
    assert "POTENTIAL" in res["system_behavior"]


def test_case_2_onion_sunflower_oil_ambiguous():
    res = run_case_2_onion_sunflower_oil()
    assert res["case_id"] == "CASE_2_ONION_SUNFLOWER_OIL"
    assert "ambiguous" in res["system_behavior"]


def test_case_3_contains_statement_strong_evidence():
    res = run_case_3_contains_statement()
    assert res["case_id"] == "CASE_3_CONTAINS_STATEMENT"
    assert "DETECTED" in res["system_behavior"]


def test_case_4_soybean_oil_curated_mapping():
    res = run_case_4_soybean_oil()
    assert res["case_id"] == "CASE_4_SOYBEAN_OIL"
    assert "DETECTED" in res["system_behavior"]


def test_case_5_nested_milk_hierarchical_extraction():
    res = run_case_5_nested_milk()
    assert res["case_id"] == "CASE_5_NESTED_MILK"
    assert "NESTED_INGREDIENT" in res["system_behavior"]


def test_case_6_oreo_uncertain_exclusion():
    res = run_case_6_oreo_uncertain()
    assert res["case_id"] == "CASE_6_OREO_UNCERTAIN"
    assert "0.5954" in res["raw_evidence"] or "0.5954" in str(res["system_behavior"]) or "UNCERTAIN" in res["raw_evidence"]


def test_error_category_summary_table():
    summary = get_error_category_summary()
    assert len(summary) == 10
    categories = {item["category"]: item["status"] for item in summary}
    assert categories["OCR error"] == "OBSERVED"
    assert categories["Fuzzy-match uncertainty"] == "OBSERVED"
    assert categories["Normalization exact-match failure"] == "NOT_OBSERVED_IN_CURRENT_SAMPLES"
