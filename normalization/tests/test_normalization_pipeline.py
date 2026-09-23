from normalization.normalizer import normalize_ingredient


def test_curated_allergen_mapping_and_provenance():
    result = normalize_ingredient("  SOY    LECITHIN  ")
    assert (result.normalized_term, result.canonical_concept, result.allergen) == ("soy lecithin", "soy", "SOY")
    assert (result.match_type, result.confidence, result.provenance) == ("curated_exact", 1.0, "curated_dictionary")


def test_milk_and_wheat_use_curated_allergen_knowledge():
    milk = normalize_ingredient("milk")
    wheat = normalize_ingredient("wheat flour")
    assert (milk.canonical_concept, milk.allergen) == ("milk", "MILK")
    assert (wheat.canonical_concept, wheat.allergen) == ("wheat", "WHEAT")


def test_dataset_compact_forms_are_known_without_hardcoded_corrections():
    for raw, expected in [
        ("citricacid", "citric acid"),
        ("thiaminmononitrate", "thiamin mononitrate"),
        ("malted barleyflour", "malted barley flour"),
        ("calciumsulfate", "calcium sulfate"),
    ]:
        result = normalize_ingredient(raw)
        assert result.normalized_term == expected
        assert result.status == "known"
        assert result.provenance == "dataset_vocabulary"


def test_dataset_candidate_is_not_auto_accepted_below_threshold():
    result = normalize_ingredient("soy leotain")
    assert result.status == "candidate"
    assert result.normalized_term == "soy lecithin"
    assert result.allergen == "SOY"
    assert result.confidence < 0.90
    assert result.candidate_matches[0].frequency is not None


def test_partial_candidate_segmentation_preserves_unknown_text():
    result = normalize_ingredient("onion sunflower oil")
    assert result.status == "ambiguous"
    assert result.provenance == "candidate_segmentation"
    assert result.unresolved_text == "onion sunflower oil"
    assert result.candidate_matches[0].candidate == "sunflower oil"


def test_low_confidence_unknown_is_not_forced_to_a_match():
    result = normalize_ingredient("completelyunknowningredientxyz")
    assert result.status == "unknown"
    assert result.normalized_term is None
    assert result.provenance == "unknown"


def test_dataset_threshold_is_configurable():
    candidate = normalize_ingredient("soy leotain", dataset_threshold=0.99)
    assert candidate.status == "candidate"


def test_direct_nested_expression_keeps_the_parent_term_explainable():
    result = normalize_ingredient("vegetable oil (soybean)")
    assert result.cleaned_term == "vegetable oil"
    assert result.normalized_term == "vegetable oil"
    assert result.status == "known"
