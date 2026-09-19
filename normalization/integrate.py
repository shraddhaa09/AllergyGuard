import ast
import json
from pathlib import Path

import pandas as pd

from .normalizer import normalize_ingredient


INPUT_FILE = Path("data/raw/allergyguard_baseline_results.csv")
OUTPUT_FILE = Path("data/processed/normalized_evidence.csv")


def parse_evidence(value):
    """
    Convert the ingredient_evidence string from the CSV
    into a Python dictionary safely.
    """

    if pd.isna(value) or not str(value).strip():
        return {}

    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return {}


def normalize_evidence(evidence):
    """
    Normalize every raw ingredient term while preserving
    the original allergen grouping.
    """

    normalized_records = []

    for allergen, ingredients in evidence.items():

        for ingredient in ingredients:

            result = normalize_ingredient(ingredient)

            normalized_records.append({
                "source_allergen": allergen,
                "raw_term": result.raw_term,
                "normalized_term": result.normalized_term,
                "canonical_concept": result.canonical_concept,
                "match_type": result.match_type,
                "confidence": result.confidence,
                "status": result.status
            })

    return normalized_records


def main():

    print("Loading baseline results...")

    df = pd.read_csv(INPUT_FILE)

    records = []

    for _, row in df.iterrows():

        evidence = parse_evidence(
            row["ingredient_evidence"]
        )

        normalized = normalize_evidence(evidence)

        for item in normalized:

            records.append({
                "image": row["image"],
                **item
            })

    output_df = pd.DataFrame(records)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nNormalization completed.")
    print(f"Input : {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Records: {len(output_df)}")

    if not output_df.empty:
        print("\nNormalized evidence:")
        print(output_df.to_string(index=False))


if __name__ == "__main__":
    main()