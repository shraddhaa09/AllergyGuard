# AllergyGuard End-to-End Evaluation Report

## 1. Evaluation Scope
- **Pipeline Description:** post-OCR end-to-end pipeline evaluation
- **Verified Samples (2):** food_ingredients.webp, random.jpg
- **Uncertain Samples (1):** oreo.jpg
- **Excluded Samples (2):** restaurant.jpg, test_image.jpg
- **Evaluated Allergens:** WHEAT, SOY, MILK

## 2. Ground-Truth Definition
- `food_ingredients.webp`: `[WHEAT, SOY, MILK]` (Verified explicitly via label CONTAINS statement)
- `random.jpg`: `[]` (Verified negative via manual inspection of full ingredient list)
- `oreo.jpg`: Excluded from quantitative metrics due to blurry image (UNCERTAIN)
- Note: Missing ground-truth allergens in unverified samples are not assumed to be allergen-free.

## 3. Current Pipeline Metrics (Strict Exact-Detection)
| Allergen | TP | TN | FP | FN | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|---|---|---|
| WHEAT | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| SOY | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| MILK | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| **Overall (Micro)** | **3** | **3** | **0** | **0** | **1.0000** | **1.0000** | **1.0000** | **3** |

## 4. Baseline Metrics
| Allergen | TP | TN | FP | FN | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|---|---|---|
| WHEAT | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| SOY | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| MILK | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| **Overall (Micro)** | **3** | **3** | **0** | **0** | **1.0000** | **1.0000** | **1.0000** | **3** |

## 5. Baseline vs Current Pipeline Comparison
**Comparison Category:** small verified evaluation-set comparison

> **IMPORTANT:** These metrics are based on only 2 verified images and should not be interpreted as general model accuracy.

Both baseline and current pipeline achieved identical strict confusion metrics on this small verified set (3 TP, 3 TN, 0 FP, 0 FN).

## 6. Per-Image Prediction Table
| Image | Allergen | Ground Truth | Baseline | Current Pipeline |
|---|---|---|---|---|
| `food_ingredients.webp` | WHEAT | PRESENT | CONFIRMED | DETECTED |
| `food_ingredients.webp` | SOY | PRESENT | CONFIRMED | DETECTED |
| `food_ingredients.webp` | MILK | PRESENT | CONFIRMED | DETECTED |
| `random.jpg` | WHEAT | ABSENT | NOT_DETECTED | NOT_DETECTED |
| `random.jpg` | SOY | ABSENT | NOT_DETECTED | NOT_DETECTED |
| `random.jpg` | MILK | ABSENT | NOT_DETECTED | NOT_DETECTED |

## 7. Limitations
- These metrics are based on only 2 verified images and should not be interpreted as general model accuracy.
- The evaluation measures post-OCR pipeline processing using stored baseline OCR text, not fresh image-to-allergen accuracy.
- Uncertain sample (oreo.jpg) and excluded non-packaged/blurry images were excluded from quantitative metrics.
- Small evaluation set prevents statistically significant conclusions regarding generalization.
