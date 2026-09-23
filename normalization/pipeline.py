import pandas as pd

from .ingredient_extractor import hierarchical_extract_ingredients
from .normalizer import normalize_ingredients
from .evidence_fusion import assess_allergens
from .risk_assessment import assess_personalized_risk
from .user_profile import AllergySeverity, UserAllergy, UserProfile
from .candidate_segmenter import generate_candidate_segments

INPUT_FILE = "data/raw/allergyguard_baseline_results.csv"

# Demonstration only. A UI, API, or user account should supply the real profile.
DEMO_PROFILE = UserProfile([
    UserAllergy("WHEAT", AllergySeverity.HIGH, True),
    UserAllergy("SOY", AllergySeverity.HIGH, True),
    UserAllergy("MILK", AllergySeverity.HIGH, True),
])


def process_image(row, profile: UserProfile | None = None):
    text = row["ingredient_text"]

    # ---------------------------------------------------------
    # 1. Extract hierarchical ingredient evidence
    # ---------------------------------------------------------

    evidence = hierarchical_extract_ingredients(
        text,
        image=row["image"],
        source="paddleocr"
    )

    ingredients = [
        item.cleaned_text
        for item in evidence
    ]

    # ---------------------------------------------------------
    # 2. Normalization
    # ---------------------------------------------------------

    normalized = normalize_ingredients(ingredients)

    allergen_evidence, allergen_assessments = assess_allergens(
        normalized,
        evidence,
        source_text=text,
    )
    product_risk = assess_personalized_risk(profile, allergen_assessments) if profile else None

    return ingredients, normalized, allergen_evidence, allergen_assessments, product_risk


def main():

    df = pd.read_csv(INPUT_FILE)

    for _, row in df.iterrows():

        image = row["image"]

        (
            ingredients,
            normalized,
            allergen_evidence,
            allergen_assessments,
            product_risk,
        ) = process_image(row, DEMO_PROFILE)

        print("\n" + "=" * 80)
        print(f"IMAGE: {image}")
        print("=" * 80)

        if not ingredients:

            print("No ingredient section detected.")

        # -----------------------------------------------------
        # RAW INGREDIENT TERMS
        # -----------------------------------------------------

        print("\nRAW INGREDIENT TERMS:")

        for ingredient in ingredients:

            print(f"  - {ingredient}")

        # -----------------------------------------------------
        # EXPLAINABLE NORMALIZATION RESULTS
        # -----------------------------------------------------

        print("\nNORMALIZATION RESULTS:")

        for ingredient, result in zip(
            ingredients,
            normalized
        ):

            print(f"\n  RAW: {ingredient}")
            print(f"  CLEANED: {result.cleaned_term}")
            print(f"  NORMALIZED: {result.normalized_term}")
            print(f"  CANONICAL: {result.canonical_concept}")
            print(f"  ALLERGEN: {result.allergen}")
            print(f"  MATCH: {result.match_type} | confidence={result.confidence:.3f}")
            print(f"  STATUS: {result.status} | provenance={result.provenance}")
            if result.candidate_matches:
                print("  CANDIDATES:")
                for candidate in result.candidate_matches:
                    print(
                        f"    - {candidate.candidate}"
                        f" | score={candidate.similarity:.3f}"
                        f" | frequency={candidate.frequency}"
                        f" | allergen={candidate.allergen}"
                    )

        print("\nALLERGEN EVIDENCE:")
        if not allergen_evidence:
            print("  No allergen evidence generated from available ingredients.")
        for item in allergen_evidence:
            print(
                f"  - {item.allergen}: {item.ingredient}"
                f" | {item.evidence_type}"
                f" | confidence={item.confidence:.3f}"
                f" | source={item.source}"
            )

        print("\nFINAL ALLERGEN ASSESSMENT:")
        for assessment in allergen_assessments:
            print(
                f"  - {assessment.allergen}: {assessment.status}"
                f" | confidence={assessment.confidence:.3f}"
                f" | evidence={len(assessment.evidence)}"
            )
            print(f"    {assessment.explanation}")

        print("\nPERSONALIZED RISK ASSESSMENT (DEMO PROFILE):")
        print(f"  OVERALL: {product_risk.overall_risk}")
        print(f"  WARNINGS: {' '.join(product_risk.warnings)}")
        for result in product_risk.allergen_results:
            print(
                f"  - {result.allergen}: {result.risk_level}"
                f" | assessment={result.assessment_status}"
                f" | confidence={result.confidence:.3f}"
            )
            print(f"    {result.reason}")


if __name__ == "__main__":
    main()
