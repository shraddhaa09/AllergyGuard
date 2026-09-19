import pandas as pd

from .ingredient_extractor import extract_ingredients
from .normalizer import normalize_ingredients


INPUT_FILE = "data/raw/allergyguard_baseline_results.csv"


def process_image(row):
    """
    Extract and normalize ingredients from one baseline record.
    """

    text = row["ingredient_text"]

    ingredients = extract_ingredients(text)

    normalized = normalize_ingredients(ingredients)

    return ingredients, normalized


def main():

    df = pd.read_csv(INPUT_FILE)

    for _, row in df.iterrows():

        image = row["image"]

        ingredients, normalized = process_image(row)

        print("\n" + "=" * 80)
        print(f"IMAGE: {image}")
        print("=" * 80)

        if not ingredients:
            print("No ingredient section detected.")
            continue

        print("\nRAW INGREDIENT TERMS:")

        for ingredient in ingredients:
            print(f"  - {ingredient}")

        print("\nNORMALIZED TERMS:")

        for result in normalized:
            print(
                f"  - {result.raw_term}"
                f" -> {result.normalized_term}"
                f" | {result.match_type}"
                f" | confidence={result.confidence:.4f}"
                f" | {result.status}"
            )


if __name__ == "__main__":
    main()