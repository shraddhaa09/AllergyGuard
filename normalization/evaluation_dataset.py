"""
Utilities for loading and filtering AllergyGuard evaluation data.

This module only handles dataset metadata and ground-truth labels.
It does not perform model evaluation or calculate accuracy.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd


DEFAULT_GROUND_TRUTH = Path("data/raw/ground_truth.csv")


VERIFIED = "VERIFIED"
UNCERTAIN = "UNCERTAIN"
EXCLUDED = "EXCLUDED"


@dataclass
class EvaluationRecord:
    image: str
    valid_food_label: bool
    ingredient_list_available: bool
    contains_statement_available: bool
    ground_truth_allergens: List[str]
    annotation_status: str
    annotation_source: str


def _parse_allergens(value) -> List[str]:
    """
    Convert a ground-truth allergen field into a normalized list.

    Missing/empty values become [].

    IMPORTANT:
    [] means that no allergen label was provided.
    It does NOT mean that the product is confirmed allergen-free.
    """

    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    return [
        allergen.strip().upper()
        for allergen in text.split(",")
        if allergen.strip()
    ]


def load_ground_truth(
    path: str | Path = DEFAULT_GROUND_TRUTH,
) -> List[EvaluationRecord]:
    """
    Load ground-truth metadata from CSV.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Ground-truth file not found: {path}"
        )

    dataframe = pd.read_csv(path)

    required_columns = {
        "image",
        "valid_food_label",
        "ingredient_list_available",
        "contains_statement_available",
        "ground_truth_allergens",
        "annotation_status",
        "annotation_source",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Ground-truth CSV is missing columns: {sorted(missing)}"
        )

    records: List[EvaluationRecord] = []

    for _, row in dataframe.iterrows():
        records.append(
            EvaluationRecord(
                image=str(row["image"]),
                valid_food_label=bool(row["valid_food_label"]),
                ingredient_list_available=bool(
                    row["ingredient_list_available"]
                ),
                contains_statement_available=bool(
                    row["contains_statement_available"]
                ),
                ground_truth_allergens=_parse_allergens(
                    row["ground_truth_allergens"]
                ),
                annotation_status=str(
                    row["annotation_status"]
                ).strip().upper(),
                annotation_source=str(
                    row["annotation_source"]
                ),
            )
        )

    return records


def get_verified_samples(
    records: List[EvaluationRecord],
) -> List[EvaluationRecord]:
    """Return only verified evaluation samples."""

    return [
        record
        for record in records
        if record.annotation_status == VERIFIED
    ]


def get_uncertain_samples(
    records: List[EvaluationRecord],
) -> List[EvaluationRecord]:
    """Return uncertain samples separately from quantitative evaluation."""

    return [
        record
        for record in records
        if record.annotation_status == UNCERTAIN
    ]


def get_excluded_samples(
    records: List[EvaluationRecord],
) -> List[EvaluationRecord]:
    """Return samples explicitly excluded from evaluation."""

    return [
        record
        for record in records
        if record.annotation_status == EXCLUDED
    ]


def main() -> None:
    records = load_ground_truth()

    verified = get_verified_samples(records)
    uncertain = get_uncertain_samples(records)
    excluded = get_excluded_samples(records)

    print("AllergyGuard Evaluation Dataset")
    print("=" * 50)

    print(f"Total records: {len(records)}")
    print(f"Verified records: {len(verified)}")
    print(f"Uncertain records: {len(uncertain)}")
    print(f"Excluded records: {len(excluded)}")

    print("\nVERIFIED:")
    for record in verified:
        print(
            f"  - {record.image}"
            f" → {record.ground_truth_allergens}"
        )

    print("\nUNCERTAIN:")
    for record in uncertain:
        print(f"  - {record.image}")

    print("\nEXCLUDED:")
    for record in excluded:
        print(f"  - {record.image}")

    print(
        "\nNote: missing ground-truth allergens are not "
        "interpreted as allergen-free."
    )


if __name__ == "__main__":
    main()