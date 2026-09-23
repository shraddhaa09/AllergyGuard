"""Small coverage report for normalization output; this is not accuracy."""

from collections import Counter
import pandas as pd

from .ingredient_extractor import hierarchical_extract_ingredients
from .normalizer import normalize_ingredients


INPUT_FILE = "data/raw/allergyguard_baseline_results.csv"


def main() -> None:
    dataframe = pd.read_csv(INPUT_FILE)
    results = []
    for _, row in dataframe.iterrows():
        evidence = hierarchical_extract_ingredients(row["ingredient_text"])
        results.extend(normalize_ingredients([item.cleaned_text for item in evidence]))

    counts = Counter(result.status for result in results)
    match_counts = Counter(result.match_type for result in results)
    total = len(results)
    matched = sum(counts[status] for status in ("known", "candidate", "ambiguous"))
    average_confidence = sum(result.confidence for result in results) / total if total else 0.0
    print(f"Total terms: {total}")
    for status in ("known", "candidate", "ambiguous", "unknown"):
        count = counts[status]
        print(f"{status}: {count} ({count / total:.1%}" + ")" if total else f"{status}: 0 (0.0%)")
    print("Match methods:")
    for match_type, count in sorted(match_counts.items()):
        print(f"  {match_type}: {count} ({count / total:.1%})")
    print(f"Coverage (non-unknown): {matched / total:.1%}" if total else "Coverage: 0.0%")
    print(f"Average matching confidence: {average_confidence:.3f}")
    print("Note: coverage and matching confidence are not accuracy or probability.")


if __name__ == "__main__":
    main()
