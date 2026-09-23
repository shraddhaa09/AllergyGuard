from normalization.evidence_fusion import assess_allergens, extract_contains_evidence
from normalization.ingredient_extractor import hierarchical_extract_ingredients
from normalization.normalizer import normalize_ingredient, normalize_ingredients


def _assessment_for(results, allergen, extracted=None, text=None):
    _, assessments = assess_allergens(results, extracted, text)
    return next(item for item in assessments if item.allergen == allergen)


def test_direct_wheat_soy_and_milk_evidence_is_detected():
    results = normalize_ingredients(["wheat flour", "soy lecithin", "milk"])
    assert _assessment_for(results, "WHEAT").status == "DETECTED"
    assert _assessment_for(results, "SOY").status == "DETECTED"
    assert _assessment_for(results, "MILK").status == "DETECTED"


def test_nested_whey_evidence_is_traced_as_nested():
    extracted = hierarchical_extract_ingredients("INGREDIENTS: BREAD (WHEY)")
    results = normalize_ingredients([item.cleaned_text for item in extracted])
    evidence, assessments = assess_allergens(results, extracted)
    milk_evidence = next(item for item in evidence if item.allergen == "MILK")
    assert milk_evidence.evidence_type == "NESTED_INGREDIENT"
    assert next(item for item in assessments if item.allergen == "MILK").status == "DETECTED"


def test_soybean_oil_is_soy_evidence():
    assessment = _assessment_for([normalize_ingredient("soybean oil")], "SOY")
    assert assessment.status == "DETECTED"
    assert assessment.evidence[0].canonical_concept == "soy"


def test_unknown_does_not_invent_allergen_evidence():
    assessment = _assessment_for([normalize_ingredient("completelyunknowningredientxyz")], "SOY")
    assert assessment.status == "INSUFFICIENT_EVIDENCE"
    assert assessment.evidence == []


def test_fuzzy_candidate_is_potential_not_detected():
    assessment = _assessment_for([normalize_ingredient("soy leotain")], "SOY")
    assert assessment.status == "POTENTIAL"
    assert assessment.evidence[0].evidence_type == "FUZZY_NORMALIZATION"
    assert assessment.evidence[0].provenance == "dataset_vocabulary"


def test_partial_non_allergen_candidate_creates_no_allergen_evidence():
    assessment = _assessment_for([normalize_ingredient("onion sunflower oil")], "SOY")
    assert assessment.status == "INSUFFICIENT_EVIDENCE"


def test_contains_statements_are_strong_and_traceable():
    evidence = extract_contains_evidence("CONTAINS: WHEAT, SOY, MILK")
    assert {item.allergen for item in evidence} == {"WHEAT", "SOY", "MILK"}
    assert all(item.source == "label_contains_statement" for item in evidence)
    assert _assessment_for([], "SOY", text="CONTAINS: WHEAT, SOY, MILK").status == "DETECTED"


def test_duplicate_evidence_is_not_double_counted():
    result = normalize_ingredient("soy lecithin")
    assessment = _assessment_for([result, result], "SOY")
    assert len(assessment.evidence) == 1
    assert assessment.confidence == 1.0


def test_known_non_allergen_ingredients_are_not_detected():
    assessment = _assessment_for(normalize_ingredients(["rice flour", "sunflower oil"]), "MILK")
    assert assessment.status == "NOT_DETECTED"
