from normalization.risk_assessment import RiskLevel, assess_personalized_risk
from normalization.schemas import AllergenAssessment, AllergenEvidence
from normalization.user_profile import AllergySeverity, UserAllergy, UserProfile


def _assessment(allergen, status, confidence=1.0, evidence=None):
    return AllergenAssessment(allergen, status, confidence, evidence or [], "test assessment")


def _profile(*allergens):
    return UserProfile([UserAllergy(allergen, AllergySeverity.HIGH, True) for allergen in allergens])


def test_detected_profile_allergen_is_high_with_supporting_data():
    evidence = [AllergenEvidence("WHEAT", "wheat flour", "wheat", "NORMALIZED_INGREDIENT", "ingredient_list", 1.0, "curated_dictionary", "WHEAT FLOUR", "strong")]
    result = assess_personalized_risk(_profile("WHEAT"), [_assessment("WHEAT", "DETECTED", evidence=evidence)])
    item = result.allergen_results[0]
    assert (item.risk_level, item.supporting_ingredients, item.provenance) == (RiskLevel.HIGH, ["wheat flour"], ["curated_dictionary"])


def test_potential_is_medium_and_not_detected_is_low():
    soy = assess_personalized_risk(_profile("SOY"), [_assessment("SOY", "POTENTIAL", 0.77)])
    milk = assess_personalized_risk(_profile("MILK"), [_assessment("MILK", "NOT_DETECTED", 0.0)])
    assert soy.overall_risk == RiskLevel.MEDIUM
    assert milk.overall_risk == RiskLevel.LOW
    assert "safe to eat" not in milk.warnings[0].lower()


def test_insufficient_and_no_match_are_distinct():
    insufficient = assess_personalized_risk(_profile("MILK"), [_assessment("MILK", "INSUFFICIENT_EVIDENCE", 0.0)])
    no_match = assess_personalized_risk(_profile("PEANUT"), [_assessment("WHEAT", "DETECTED")])
    assert insufficient.overall_risk == RiskLevel.INSUFFICIENT_EVIDENCE
    assert no_match.overall_risk == RiskLevel.NO_MATCH


def test_overall_precedence_and_empty_profile():
    profile = _profile("SOY", "MILK")
    medium = assess_personalized_risk(profile, [_assessment("SOY", "POTENTIAL"), _assessment("MILK", "INSUFFICIENT_EVIDENCE")])
    insufficient = assess_personalized_risk(profile, [_assessment("SOY", "NOT_DETECTED"), _assessment("MILK", "INSUFFICIENT_EVIDENCE")])
    empty = assess_personalized_risk(UserProfile(), [_assessment("MILK", "DETECTED")])
    assert medium.overall_risk == RiskLevel.MEDIUM
    assert insufficient.overall_risk == RiskLevel.INSUFFICIENT_EVIDENCE
    assert empty.overall_risk == RiskLevel.NO_MATCH


def test_conflicting_assessments_use_detected_precedence_and_preserve_note():
    result = assess_personalized_risk(_profile("SOY"), [_assessment("SOY", "NOT_DETECTED"), _assessment("SOY", "DETECTED")])
    item = result.allergen_results[0]
    assert item.risk_level == RiskLevel.HIGH
    assert item.conflict_note is not None


def test_multiple_profile_allergies_with_detected_evidence_have_high_overall_risk():
    result = assess_personalized_risk(_profile("WHEAT", "SOY"), [_assessment("WHEAT", "DETECTED"), _assessment("SOY", "NOT_DETECTED")])
    assert result.overall_risk == RiskLevel.HIGH
    assert result.matched_allergens == ["WHEAT"]


def test_multiple_potential_evidence_remains_medium():
    result = assess_personalized_risk(_profile("WHEAT", "SOY"), [_assessment("WHEAT", "POTENTIAL"), _assessment("SOY", "POTENTIAL")])
    assert result.overall_risk == RiskLevel.MEDIUM


def test_partial_evidence_preserves_unresolved_supporting_text():
    evidence = [AllergenEvidence("SOY", "soy lecithin", "soy", "PARTIAL_MATCH", "ingredient_list", 0.75, "candidate_segmentation", "noisy label text", "weak")]
    result = assess_personalized_risk(_profile("SOY"), [_assessment("SOY", "POTENTIAL", 0.75, evidence)])
    item = result.allergen_results[0]
    assert item.unresolved_text == ["noisy label text"]
    assert result.unresolved_evidence == ["noisy label text"]


def test_empty_product_assessments_are_insufficient_for_an_allergic_profile():
    result = assess_personalized_risk(_profile("MILK"), [])
    assert result.overall_risk == RiskLevel.INSUFFICIENT_EVIDENCE
    assert result.allergen_results[0].assessment_status == "INSUFFICIENT_EVIDENCE"
