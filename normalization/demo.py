"""
demo.py
--------
Shows how allergy_engine plugs into the existing pipeline, right after
your Ingredient Normalization stage and before the response is returned
from POST /api/analyze.

    Ingredient Normalization (already built)
              |
              v
    allergy_engine.assess_allergies()          <- Phase 1
              |
              v
    allergy_engine.generate_explainable_report() <- Phases 2+3
              |
              v
    JSON response to the React frontend
"""

import json

from .allergen_knowledge import assess_allergens
from .report_generator import generate_explainable_report

def analyze(product_name, normalized_ingredients, contains_terms,
            has_ingredient_text, ocr_confidence, user_allergies):
    assessments = assess_allergens(
        normalized_ingredients,
        contains_terms,
        has_ingredient_text=has_ingredient_text,
        ocr_confidence=ocr_confidence,
    )
    report = generate_explainable_report(
        assessments,
        user_allergies,
        product_name=product_name,
        ocr_confidence=ocr_confidence,
    )
    return report.to_dict()


if __name__ == "__main__":
    # food_ingredients.webp, from the project's own verified evaluation set
    result_1 = analyze(
        product_name="food_ingredients.webp",
        normalized_ingredients=["WHEAT FLOUR", "SOY LECITHIN", "MILK", "SOYBEAN OIL"],
        contains_terms=["WHEAT", "SOY", "MILK"],
        has_ingredient_text=True,
        ocr_confidence=0.9545,
        user_allergies={"WHEAT": "moderate", "SOY": "mild", "MILK": "severe", "PEANUT": None},
    )
    print("=== food_ingredients.webp ===")
    print(json.dumps(result_1, indent=2))

    # oreo.jpg, the project's own UNCERTAIN / low-quality case
    result_2 = analyze(
        product_name="oreo.jpg",
        normalized_ingredients=[],
        contains_terms=[],
        has_ingredient_text=False,
        ocr_confidence=0.5954,
        user_allergies={"WHEAT": "severe", "SOY": None, "MILK": None},
    )
    print("\n=== oreo.jpg ===")
    print(json.dumps(result_2, indent=2))

    # a new expanded-coverage example (egg + peanut), demonstrating Phase 1
    result_3 = analyze(
        product_name="sample_snack_bar.jpg",
        normalized_ingredients=["OATS", "PEANUT BUTTER", "EGG WHITE", "HONEY"],
        contains_terms=[],
        has_ingredient_text=True,
        ocr_confidence=0.93,
        user_allergies={"PEANUT": "severe", "EGG": "mild", "SHELLFISH": None},
    )
    print("\n=== sample_snack_bar.jpg (expanded allergy coverage) ===")
    print(json.dumps(result_3, indent=2))