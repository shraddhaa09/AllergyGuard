import pandas as pd
from pathlib import Path

from normalization.build_ingredient_vocabulary import build_vocabulary, extract_ingredient_terms
from normalization.dataset_matcher import dataset_match
from normalization.ingredient_vocabulary import load_vocabulary


def test_recursive_extraction_omits_explanatory_parentheticals():
    assert extract_ingredient_terms("soy lecithin (emulsifier)") == ["soy lecithin"]
    assert extract_ingredient_terms("ascorbic acid (vitamin c)") == ["ascorbic acid"]


def test_recursive_extraction_handles_nested_and_square_brackets():
    terms = extract_ingredient_terms(
        "enriched wheat flour [wheat flour, niacin, blend (reduced iron, folic acid)]"
    )
    assert terms == [
        "enriched wheat flour",
        "wheat flour",
        "niacin",
        "blend",
        "reduced iron",
        "folic acid",
    ]


def test_single_item_parentheticals_can_be_ingredients():
    assert extract_ingredient_terms("vegetable oil (soybean)") == ["vegetable oil", "soybean"]
    assert extract_ingredient_terms("whey (milk)") == ["whey", "milk"]


def test_vocabulary_building_preserves_frequency():
    dataframe = pd.DataFrame(
        {"ingredients": ["soy lecithin (emulsifier), whey (milk)", "soy lecithin"]}
    )
    vocabulary = build_vocabulary(dataframe).set_index("raw_term")
    assert vocabulary.loc["soy lecithin", "frequency"] == 2
    assert vocabulary.loc["whey", "frequency"] == 1
    assert vocabulary.loc["milk", "frequency"] == 1
    assert "emulsifier" not in vocabulary.index


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ingredient_vocabulary.csv"


def test_dataset_matcher_fuzzy_match_and_threshold():
    path = FIXTURE_PATH

    match = dataset_match("thiaminmononitrate", threshold=0.95, vocabulary_path=path)
    assert match["candidate"] == "thiamin mononitrate"
    assert match["score"] == 1.0
    assert match["match_type"] == "dataset_exact"
    assert match["accepted"] is True
    assert match["candidates"][0].frequency == 2
    low_confidence = dataset_match("unrelated text", threshold=0.95, vocabulary_path=path)
    assert low_confidence is None


def test_vocabulary_loader_reads_csv():
    assert load_vocabulary(FIXTURE_PATH).to_dict("records") == [
        {"raw_term": "soy lecithin", "frequency": 5},
        {"raw_term": "thiamin mononitrate", "frequency": 2},
    ]
