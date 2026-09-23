"""
Run the current AllergyGuard pipeline on verified evaluation samples.

This evaluates the post-OCR pipeline:
OCR text -> ingredient extraction -> normalization
-> allergen evidence fusion -> personalized risk.

It does NOT rerun PaddleOCR on the images.
"""

import json
from pathlib import Path

import pandas as pd

from .evaluation_dataset import load_ground_truth, get_verified_samples
from .pipeline import process_image, DEMO_PROFILE


BASELINE_FILE = Path("data/raw/allergyguard_baseline_results.csv")
OUTPUT_FILE = Path("reports/current_pipeline_predictions.json")


from dataclasses import is_dataclass, asdict


def serialize_object(item):
    if item is None:
        return None

    if hasattr(item, "model_dump"):
        return item.model_dump()

    if is_dataclass(item):
        return asdict(item)

    if hasattr(item, "__dict__"):
        return item.__dict__

    return str(item)


def serialize_normalized(item):
    return serialize_object(item)


def main():

    print("AllergyGuard Current Pipeline Evaluation")
    print("=" * 60)

    # --------------------------------------------------
    # 1. Load verified evaluation samples
    # --------------------------------------------------

    records = load_ground_truth()
    verified = get_verified_samples(records)

    print(f"Verified samples: {len(verified)}")

    # --------------------------------------------------
    # 2. Load OCR baseline results
    # --------------------------------------------------

    baseline = pd.read_csv(BASELINE_FILE)

    results = []

    # --------------------------------------------------
    # 3. Run current pipeline
    # --------------------------------------------------

    for record in verified:

        matching_rows = baseline[
            baseline["image"] == record.image
        ]

        if matching_rows.empty:
            print(f"\nWARNING: No OCR result found for {record.image}")
            continue

        row = matching_rows.iloc[0]

        print(f"\nProcessing: {record.image}")
        print("-" * 60)

        (
            ingredients,
            normalized,
            allergen_evidence,
            allergen_assessments,
            product_risk,
        ) = process_image(
            row,
            profile=DEMO_PROFILE,
        )

        print("Extracted ingredients:")
        for ingredient in ingredients:
            print(f"  - {ingredient}")

        print("\nAllergen assessments:")

        for assessment in allergen_assessments:
            print(
                f"  {assessment.allergen}: "
                f"{assessment.status}"
            )

        if product_risk is not None:
            print("\nPersonalized risk:")
            print(
                f"  Overall risk: {product_risk.overall_risk}"
            )
            print(
                f"  Explanation: {product_risk.explanation}"
            )
            for risk in product_risk.allergen_results:
                print(
                    f"  {risk.allergen}: {risk.risk_level} - {risk.reason}"
                )

        # --------------------------------------------------
        # Store structured result
        # --------------------------------------------------

        result = {
            "image": record.image,

            "ground_truth": {
                "allergens": record.ground_truth_allergens,
                "annotation_status": record.annotation_status,
                "annotation_source": record.annotation_source,
            },

            "ocr_text": row["ingredient_text"],

            "ingredients": ingredients,

            "normalized": [
                serialize_normalized(item)
                for item in normalized
            ],

            "allergen_evidence": [
                serialize_object(item)
                for item in allergen_evidence
            ],

            "allergen_assessments": [
                serialize_object(item)
                for item in allergen_assessments
            ],

            "personalized_risk": (
                serialize_object(product_risk)
                if product_risk
                else None
            ),
        }

        results.append(result)

    # --------------------------------------------------
    # 4. Save report
    # --------------------------------------------------

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            default=str,
        )

    print("\n" + "=" * 60)
    print(f"Saved predictions to:")
    print(OUTPUT_FILE)
    print(f"Samples processed: {len(results)}")


if __name__ == "__main__":
    main()