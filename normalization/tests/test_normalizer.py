from normalization.ingredient_extractor import hierarchical_extract_ingredients
from normalization.normalizer import normalize_ingredient


def test_top_level_ingredients_without_nested_terms():
    text = "INGREDIENTS: MILK, SUGAR, WHEAT FLOUR CONTAINS: WHEAT, MILK"
    items = hierarchical_extract_ingredients(text)

    top_level = [item.cleaned_text for item in items if item.level == "top_level"]

    assert top_level == ["MILK", "SUGAR", "WHEAT FLOUR"]


def test_parent_child_relationships_are_preserved():
    text = (
        "INGREDIENTS: FLOUR (WHEAT FLOUR, NIACIN), "
        "CHOCOLATE (MILK, SOY LECITHIN), SUGAR"
    )
    items = hierarchical_extract_ingredients(text)

    parent_names = {item.cleaned_text for item in items if item.level == "top_level"}
    assert {"FLOUR", "CHOCOLATE", "SUGAR"}.issubset(parent_names)

    nested = [item for item in items if item.level == "nested"]
    assert any(item.parent == "FLOUR" and item.cleaned_text == "WHEAT FLOUR" for item in nested)
    assert any(item.parent == "CHOCOLATE" and item.cleaned_text == "SOY LECITHIN" for item in nested)


def test_malformed_parentheses_are_handled_safely():
    text = "INGREDIENTS: BREAD (WHEAT, NIACIN, CHOCOLATE (MILK), SUGAR"
    items = hierarchical_extract_ingredients(text)

    values = {item.cleaned_text for item in items}
    assert "BREAD" in values
    assert "WHEAT" in values
    assert "MILK" in values


def test_missing_ingredients_section_returns_empty_list():
    text = "CONTAINS: WHEAT, MILK"
    items = hierarchical_extract_ingredients(text)
    assert items == []


def test_ocr_noise_is_preserved_with_cleaned_candidates():
    text = "INGREDIENTS: FOR BEST WHEN USED BY 5% SEMISWEET CHOCOLATE CHIPS (SUGAR, MILK, SOY LECITHIN)"
    items = hierarchical_extract_ingredients(text)

    assert any(item.raw_text.startswith("FOR BEST WHEN USED BY 5%") for item in items)
    assert any(item.cleaned_text == "SEMISWEET CHOCOLATE CHIPS" for item in items if item.level == "top_level")
    assert any(item.parent == "SEMISWEET CHOCOLATE CHIPS" and item.cleaned_text == "SOY LECITHIN" for item in items)


def test_nested_parentheses_are_extracted_without_overcleaning():
    text = "INGREDIENTS: CHOCOLATE (SUGAR (RAW CANE SUGAR), COCOA, MILK)"
    items = hierarchical_extract_ingredients(text)

    nested = [item.cleaned_text for item in items if item.level == "nested"]
    assert "RAW CANE SUGAR" in nested
    assert "COCOA" in nested
    assert "MILK" in nested


def test_unknown_ingredient_remains_unknown():
    result = normalize_ingredient("MYSTERY INGREDIENT QZX")

    assert result.status == "unknown"
    assert result.normalized_term is None
    assert result.canonical_concept is None

def test_pre_extracted_ingredient_text_without_heading():
    text = "MILK, SUGAR, WHEAT FLOUR, SOY LECITHIN"

    items = hierarchical_extract_ingredients(text)

    values = [item.cleaned_text for item in items]

    assert "MILK" in values
    assert "SUGAR" in values
    assert "WHEAT FLOUR" in values
    assert "SOY LECITHIN" in values


def test_contains_only_text_is_not_treated_as_ingredients():
    text = "CONTAINS: WHEAT, MILK"

    items = hierarchical_extract_ingredients(text)

    assert items == []

def test_ocr_spacing_is_cleaned():
    text = "UNBLEACHED ENRICHED FLOUR, SEMISWEET CHOCOLATE CHIPS, SOY LECITHIN"

    items = hierarchical_extract_ingredients(text)

    values = [item.cleaned_text for item in items]

    assert "UNBLEACHED ENRICHED FLOUR" in values
    assert "SEMISWEET CHOCOLATE CHIPS" in values
    assert "SOY LECITHIN" in values


def test_packaging_metadata_is_not_treated_as_ingredient():
    text = (
        "POTATOES, SUNFLOWER OIL, RICE FLOUR, SEA SALT, "
        "DIST. & SOLD EXCLUSIVELY BY: TRADER JOE'S, "
        "MONROVIA, CA 91016, STORE IN A COOL, DRY PLACE, SKU# 91750-89326"
    )

    items = hierarchical_extract_ingredients(text)

    values = [item.cleaned_text for item in items]

    assert "POTATOES" in values
    assert "RICE FLOUR" in values
    assert not any("TRADER JOE" in value for value in values)
    assert not any("SKU" in value for value in values)
