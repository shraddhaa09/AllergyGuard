"""Report evidence-fusion coverage on the small OCR baseline; not medical accuracy."""

from collections import Counter
import pandas as pd

from .evidence_fusion import assess_allergens
from .ingredient_extractor import hierarchical_extract_ingredients
from .normalizer import normalize_ingredients


INPUT_FILE = "data/raw/allergyguard_baseline_results.csv"


def main() -> None:
    dataframe = pd.read_csv(INPUT_FILE)
    all_results, all_evidence, all_assessments = [], [], []
    for _, row in dataframe.iterrows():
        extracted = hierarchical_extract_ingredients(row["ingredient_text"])
        normalized = normalize_ingredients([item.cleaned_text for item in extracted])
        evidence, assessments = assess_allergens(normalized, extracted, row["ingredient_text"])
        all_results.extend(normalized)
        all_evidence.extend(evidence)
        all_assessments.extend(assessments)

    print(f"Ingredients processed: {len(all_results)}")
    print(f"Known ingredients: {sum(item.status == 'known' for item in all_results)}")
    print(f"Unknown ingredients: {sum(item.status == 'unknown' for item in all_results)}")
    print("Evidence types:", dict(Counter(item.evidence_type for item in all_evidence)))
    print("Assessment statuses:", dict(Counter(item.status for item in all_assessments)))
    average = sum(item.confidence for item in all_evidence) / len(all_evidence) if all_evidence else 0.0
    print(f"Average evidence confidence: {average:.3f}")
    print("This report measures evidence coverage, not medical accuracy or validation.")


if __name__ == "__main__":
    main()
