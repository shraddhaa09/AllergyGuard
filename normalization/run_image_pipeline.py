"""
Fresh Image -> PaddleOCR -> AllergyGuard Pipeline Integration.

Executes end-to-end processing on a raw image file:
Image -> PaddleOCR -> OCR Text -> Ingredient Extraction -> Normalization
-> Allergen Evidence Fusion -> Personalized Risk Assessment.

Preserves OCR confidence separately from allergen matching confidence.
"""

import os
os.environ["FLAGS_enable_pir_api"] = "0"

from pathlib import Path
import sys
from paddleocr import PaddleOCR

from .ingredient_extractor import hierarchical_extract_ingredients
from .image_preprocessor import preprocess_image
from .normalizer import normalize_ingredients
from .evidence_fusion import assess_allergens
from .risk_assessment import assess_personalized_risk
from .user_profile import UserProfile
from .pipeline import DEMO_PROFILE

_OCR_ENGINE = None


def get_ocr_engine() -> PaddleOCR:
    """Singleton getter for PaddleOCR engine."""
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        _OCR_ENGINE = PaddleOCR(lang="en", enable_mkldnn=False)
    return _OCR_ENGINE


def run_ocr(image_path: Path) -> tuple[str, float, int]:
    """
    Run PaddleOCR on one image and return:

        full_text
        average OCR confidence
        number of detected text regions
    """

    if not image_path.exists():
        print(f"WARNING: Image file not found: {image_path}")
        return "", 0.0, 0

    try:
        engine = get_ocr_engine()

        result = engine.predict(
            str(image_path),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_side_len=1600,
        )

        if not result:
            return "", 0.0, 0

        first_res = (
            result[0]
            if isinstance(result, list) and len(result) > 0
            else result
        )

        texts = []
        scores = []

        if hasattr(first_res, "get"):

            raw_texts = first_res.get("rec_texts") or []
            raw_scores = first_res.get("rec_scores") or []

            for text, score in zip(raw_texts, raw_scores):

                if text:
                    texts.append(str(text))
                    scores.append(float(score))

        elif hasattr(first_res, "rec_texts"):

            raw_texts = getattr(first_res, "rec_texts") or []
            raw_scores = getattr(first_res, "rec_scores") or []

            for text, score in zip(raw_texts, raw_scores):

                if text:
                    texts.append(str(text))
                    scores.append(float(score))

        elif isinstance(first_res, (list, tuple)):

            for line in first_res:

                if (
                    line
                    and len(line) >= 2
                    and isinstance(line[1], (tuple, list))
                ):

                    texts.append(str(line[1][0]))
                    scores.append(float(line[1][1]))

        full_text = " ".join(texts)

        avg_confidence = (
            sum(scores) / len(scores)
            if scores
            else 0.0
        )

        return (
            full_text,
            avg_confidence,
            len(scores),
        )

    except Exception as exc:

        print(
            f"WARNING: PaddleOCR execution failed "
            f"for {image_path}: {exc}"
        )

        return "", 0.0, 0
def score_ocr_result(
    text: str,
    confidence: float,
    regions: int,
) -> float:
    """
    Score OCR output specifically for food ingredient labels.
    Higher is better.
    """

    if not text.strip():
        return 0.0

    normalized_text = text.upper()

    # ------------------------------------------
    # Basic quality
    # ------------------------------------------

    score = confidence * 50

    # More useful text, but cap the contribution
    text_score = min(len(text) / 500, 1.0) * 15
    score += text_score

    # ------------------------------------------
    # Ingredient-related vocabulary
    # ------------------------------------------

    useful_words = [
        "INGREDIENT",
        "INGREDIENTS",
        "CONTAINS",
        "FLOUR",
        "WHEAT",
        "MILK",
        "SOY",
        "SOYBEAN",
        "EGG",
        "PEANUT",
        "NUT",
        "BUTTER",
        "OIL",
        "SUGAR",
        "SALT",
        "STARCH",
        "CREAM",
        "COCOA",
        "CHOCOLATE",
        "LECITHIN",
        "PROTEIN",
        "SYRUP",
        "POWDER",
    ]

    keyword_hits = sum(
        1
        for word in useful_words
        if word in normalized_text
    )

    score += min(keyword_hits * 5, 25)

    # ------------------------------------------
    # Ingredient section markers
    # ------------------------------------------

    if "INGREDIENTS" in normalized_text:
        score += 15

    if "CONTAINS" in normalized_text:
        score += 15

    # OCR output with very little text is suspicious
    if len(text.strip()) < 30:
        score -= 10

    # ------------------------------------------
    # Garbage penalty
    # ------------------------------------------

    alphanumeric = sum(
        char.isalnum() or char.isspace()
        for char in text
    )

    if len(text) > 0:
        clean_ratio = alphanumeric / len(text)

        if clean_ratio < 0.65:
            score -= 10

    # ------------------------------------------
    # Region contribution
    # ------------------------------------------

    score += min(regions / 100, 1.0) * 5

    return score

def process_fresh_image(
    image_path: str | Path,
    profile: UserProfile | None = DEMO_PROFILE,
):
    """
    Process a fresh food image using multiple OCR versions.

    The OCR result with the strongest combination of
    confidence and detected text is selected.
    """

    path = Path(image_path)

    # ==========================================
    # CREATE PREPROCESSED IMAGES
    # ==========================================

    try:

        processed_images = preprocess_image(
            path
        )

    except Exception as exc:

        print(
            f"WARNING: Image preprocessing failed: {exc}"
        )

        processed_images = [path]

    # Always include the original image
    ocr_candidates = [path] + processed_images

    best_text = ""
    best_confidence = 0.0
    best_regions = 0
    best_image = path
    best_score = 0.0

    # ==========================================
    # RUN OCR ON EVERY VERSION
    # ==========================================

    for candidate in ocr_candidates:

        print(
            f"Running OCR on: {candidate}"
        )

        text, confidence, regions = run_ocr(
            candidate
        )

        print(
            f"  confidence={confidence:.4f}, "
            f"regions={regions}, "
            f"text_length={len(text)}"
        )

        # --------------------------------------
        # Score the OCR result
        # --------------------------------------

        if not text.strip():

            continue

        # More detected text regions is useful,
        # but confidence remains the main factor.

        score = score_ocr_result(
            text,
            confidence,
            regions,
        )

        print(
            f"  OCR quality score={score:.2f}"
        )

        if score > best_score:

            best_score = score
            best_text = text
            best_confidence = confidence
            best_regions = regions
            best_image = candidate

    # ==========================================
    # OCR SUMMARY
    # ==========================================

    ocr_summary = {
        "avg_confidence": round(
            best_confidence,
            4,
        ),
        "region_count": best_regions,
        "selected_image": str(best_image),
    }

    # ==========================================
    # INGREDIENT EXTRACTION
    # ==========================================

    evidence = hierarchical_extract_ingredients(
        best_text,
        image=path.name,
        source="paddleocr",
    )

    ingredients = [
        item.cleaned_text
        for item in evidence
    ]

    # ==========================================
    # NORMALIZATION
    # ==========================================

    normalized = normalize_ingredients(
        ingredients
    )

    # ==========================================
    # ALLERGEN EVIDENCE
    # ==========================================

    allergen_evidence, allergen_assessments = (
        assess_allergens(
            normalized,
            evidence,
            source_text=best_text,
        )
    )

    # ==========================================
    # PERSONALIZED RISK
    # ==========================================

    product_risk = (
        assess_personalized_risk(
            profile,
            allergen_assessments,
        )
        if profile
        else None
    )

    return (
        path,
        best_text,
        ocr_summary,
        ingredients,
        normalized,
        allergen_evidence,
        allergen_assessments,
        product_risk,
    )

def main():
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "data/raw/food_ingredients.webp"

    (
        path,
        ocr_text,
        ocr_summary,
        ingredients,
        normalized,
        allergen_evidence,
        allergen_assessments,
        product_risk,
    ) = process_fresh_image(image_path, DEMO_PROFILE)

    print("\n" + "=" * 60)
    print("AllergyGuard Fresh Image Pipeline Execution")
    print("=" * 60)
    print(f"1. Image Path: {path}")
    print(f"2. OCR Text: {ocr_text if ocr_text else '[No OCR text extracted]'}")
    print(f"3. OCR Confidence Summary:")
    print(f"   - Average OCR Confidence: {ocr_summary['avg_confidence']}")
    print(f"   - OCR Regions Detected: {ocr_summary['region_count']}")

    print("\n4. Extracted Ingredients:")
    if not ingredients:
        print("   [No ingredients extracted]")
    for ing in ingredients:
        print(f"   - {ing}")

    print("\n5. Normalized Ingredients:")
    if not normalized:
        print("   [No normalized ingredients]")
    for item in normalized:
        print(
            f"   - Raw: '{item.raw_term}' -> Cleaned: '{item.cleaned_term}' "
            f"-> Normalized: '{item.normalized_term}' (Concept: {item.canonical_concept}, "
            f"Allergen: {item.allergen}, Match: {item.match_type}, Status: {item.status}, "
            f"Conf: {item.confidence:.4f})"
        )

    print("\n6. Allergen Evidence:")
    if not allergen_evidence:
        print("   [No allergen evidence found]")
    for ev in allergen_evidence:
        print(
            f"   - Allergen: {ev.allergen} | Ingredient: {ev.ingredient} "
            f"| Type: {ev.evidence_type} | Status: {ev.status} "
            f"| Conf: {ev.confidence:.4f} | Text: '{ev.supporting_text}'"
        )

    print("\n7. Allergen Assessments:")
    for assessment in allergen_assessments:
        print(
            f"   - {assessment.allergen}: {assessment.status} "
            f"(Confidence: {assessment.confidence:.4f}) - {assessment.explanation}"
        )

    print("\n8. Personalized Risk Assessment (Demo Profile):")
    if product_risk is not None:
        print(f"   - Overall Risk: {product_risk.overall_risk}")
        print(f"   - Explanation: {product_risk.explanation}")
        if product_risk.warnings:
            print(f"   - Warnings: {' '.join(product_risk.warnings)}")
        for r in product_risk.allergen_results:
            print(f"     * {r.allergen}: {r.risk_level} - {r.reason}")
    else:
        print("   [No profile specified]")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
