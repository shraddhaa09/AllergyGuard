# AllergyGuard Evaluation Report

## 1. Evaluation Objective

The objective of this evaluation is to assess the post-OCR processing pipeline of the AllergyGuard system, which includes:
- Hierarchical ingredient extraction
- Multi-stage ingredient normalization
- Allergen evidence fusion
- Personalized risk assessment

**Important Note on Pipeline Scope:** The quantitative evaluation currently begins from pre-extracted OCR text stored in baseline results (`data/raw/allergyguard_baseline_results.csv`). It is accurately described as a **post-OCR pipeline evaluation**, rather than a fresh image-to-prediction end-to-end evaluation, as PaddleOCR was not rerun during this evaluation benchmark.

---

## 2. Evaluation Dataset

The evaluation dataset (`data/raw/ground_truth.csv`) comprises 5 total image records categorized into distinct annotation status tiers:

* **Total Records:** 5
* **VERIFIED (2 records):**
  - `food_ingredients.webp` — Ground Truth: `[WHEAT, SOY, MILK]` (Verified via explicit label `CONTAINS` statement)
  - `random.jpg` — Ground Truth: `[]` (Verified negative via manual inspection of full ingredient list)
* **UNCERTAIN (1 record):**
  - `oreo.jpg` — Excluded from quantitative evaluation (label visible but photograph too blurry for reliable manual ground-truth annotation)
* **EXCLUDED (2 records):**
  - `restaurant.jpg` — Excluded (restaurant menu, not packaged food label)
  - `test_image.jpg` — Excluded (no useful food-label text)

**Dataset Scope Rationale:** UNCERTAIN and EXCLUDED samples were excluded from quantitative metrics calculation to prevent unverified or non-packaged food images from corrupting ground-truth benchmarking. Missing ground-truth labels in unverified samples are not assumed to be allergen-free.

---

## 3. Quantitative Results

Quantitative evaluation was performed across the 2 VERIFIED samples for the 3 target profile allergens (`WHEAT`, `SOY`, `MILK`), yielding 6 individual binary evaluation decisions.

### F1 Score Comparison

| Allergen | Baseline F1 | Current Pipeline F1 |
|---|---|---|
| **WHEAT** | 1.000 | 1.000 |
| **SOY** | 1.000 | 1.000 |
| **MILK** | 1.000 | 1.000 |
| **Overall (Micro)** | **1.000** | **1.000** |

### Confusion Matrix Breakdown

#### Current Pipeline
| Allergen | TP | TN | FP | FN | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|---|---|---|---|
| WHEAT | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| SOY | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| MILK | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| **Overall (Micro)** | **3** | **3** | **0** | **0** | **1.0000** | **1.0000** | **1.0000** | **3** |

#### Baseline System
| Allergen | TP | TN | FP | FN | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|---|---|---|---|
| WHEAT | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| SOY | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| MILK | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1 |
| **Overall (Micro)** | **3** | **3** | **0** | **0** | **1.0000** | **1.0000** | **1.0000** | **3** |

> **CRITICAL EVALUATION DISCLAIMER:** On the 2-image verified evaluation set, all 6 allergen decisions matched the available ground truth. The quantitative results are based on only 2 verified images and should not be interpreted as general model accuracy.

---

## 4. Baseline vs Current Pipeline

* **Factual Metric Outcome:** Both baseline and current pipeline produced the same binary allergen decisions on the available verified samples (3 True Positives, 3 True Negatives, 0 False Positives, 0 False Negatives).
* **F1 Comparison:** Therefore, this dataset does not demonstrate a numerical F1 improvement over the baseline on these 2 verified images.
* **Architectural Enhancements:** While numerical accuracy metrics are identical on this small set, the current pipeline introduces key architectural capabilities absent in the simple keyword-matching baseline:
  - Explainable multi-stage ingredient normalization (curated dictionary, compact index, candidate segmentation)
  - Full provenance tracing for every normalized concept
  - Traceable allergen evidence fusion distinguishing direct, nested, and label disclosure statements
  - Explicit uncertainty and candidate handling (preventing noisy OCR text from auto-triggering alerts)
  - Deterministic personalized risk assessment mapped to user allergy severity profiles

---

## 5. Error Analysis

System performance and uncertainty handling were evaluated across 6 key case studies:

### 1. `SOY LEOTAIN` (OCR Typo & Spelling Corruption)
* **Behavior:** Raw OCR term `SOY LEOTAIN` matched dataset candidate `soy lecithin` with similarity score ~0.7774, resulting in `status='candidate'` and `match_type='dataset_candidate'`.
* **Evidence Fusion:** Assigned `evidence_type='FUZZY_NORMALIZATION'` (`status='weak'`), yielding `AllergenAssessment` status `POTENTIAL`.
* **Handling:** The system refrains from treating corrupted text as a confirmed exact match. Because status is `candidate` (confidence < 0.95), strict detection metrics do not automatically classify it as `DETECTED`, preventing false positive alerts.

### 2. `ONION SUNFLOWER OIL` (Unseparated String / Missing Comma Separator)
* **Behavior:** The unseparated OCR token `ONION SUNFLOWER OIL` was processed by candidate segmentation, identifying the valid multi-word segment `sunflower oil` (`similarity=1.0`) while retaining `unresolved_text='ONION SUNFLOWER OIL'`.
* **Handling:** Marked as `status='ambiguous'`, `match_type='partial_match'`. The system conservatively avoids hallucinating a synthetic canonical ingredient mapping for `onion`. Sunflower oil is not mapped to any allergen in the curated knowledge base.

### 3. `CONTAINS: WHEAT, SOY, MILK` (Explicit Label Allergen Disclosure)
* **Behavior:** The explicit label disclosure statement on `food_ingredients.webp` was extracted with `evidence_type='CONTAINS_STATEMENT'`, `confidence=1.0`, `status='strong'`.
* **Handling:** Evidence fusion assigned `status='DETECTED'` for `WHEAT`, `SOY`, and `MILK`. Direct manufacturer disclosures receive highest precedence.

### 4. `SOYBEAN OIL` (Curated Allergen Mapping)
* **Behavior:** Cleaned term `soybean oil` matched the curated allergen dictionary (`match_type='curated_exact'`, `confidence=1.0`, `status='known'`).
* **Handling:** Directly mapped to canonical concept `soy` and allergen `SOY`, generating `status='strong'` evidence yielding `SOY`: `DETECTED`.

### 5. `Nested MILK` (Hierarchical Sub-Ingredient Extraction)
* **Behavior:** `MILK` inside the parenthetical structure `SEMISWEET CHOCOLATE CHIPS (SUGAR, CHOCOLATE, COCOA BUTTER, DEXTROSE, SOY LECITHIN, MILK)` was extracted with `level='nested'` and `parent='SEMISWEET CHOCOLATE CHIPS'`.
* **Handling:** Evidence fusion assigned `evidence_type='NESTED_INGREDIENT'` (`status='strong'`), yielding `MILK`: `DETECTED`.

### 6. `oreo.jpg` (Ground-Truth & Image Uncertainty)
* **Behavior:** Image `oreo.jpg` exhibited low average PaddleOCR confidence (~0.5954) due to image blurriness.
* **Handling:** Excluded from quantitative metric calculation. OCR confidence is an indicator of image quality degradation rather than proof of OCR accuracy or error. Held out as `UNCERTAIN` until manual re-annotation or higher-quality re-imaging is available.

---

## 6. Error Category Summary

The 10 standard evaluation failure categories were assessed against empirical project data:

| Category | Status | Empirical Project Evidence |
|---|---|---|
| **OCR error** | **OBSERVED** | Accent character glitch `CHOCOLATÉ` in `food_ingredients.webp`; garbled text in `oreo.jpg` (confidence 0.5954). |
| **Ingredient extraction error** | **OBSERVED** | `ONION SUNFLOWER OIL` merged without a comma in the raw OCR stream of `random.jpg`. |
| **OCR spacing error** | **OBSERVED** | `SUNFLOWERAND/ OR` (missing space) and missing spaces after commas in `random.jpg`. |
| **Normalization exact-match failure** | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | All valid non-corrupted terms in verified samples matched curated or dataset indices. |
| **Fuzzy-match uncertainty** | **OBSERVED** | Corrupted typo `SOY LEOTAIN` matched `soy lecithin` at candidate confidence 0.7774 (`POTENTIAL` status). |
| **Ambiguous ingredient** | **OBSERVED** | `ONION SUNFLOWER OIL` yielded candidate segmentation partial match (`ambiguous` status). |
| **Unknown ingredient** | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | No valid ingredient term in verified samples was left unmapped. |
| **Allergen knowledge gap** | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | Curated dictionary cleanly covered all present target allergens (WHEAT, SOY, MILK). |
| **Evidence conflict** | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | No contradictory label statements (e.g. `CONTAINS` vs ingredient list) were present. |
| **Ground-truth ambiguity** | **OBSERVED** | `oreo.jpg` photograph blurriness prevented reliable human manual ground-truth annotation. |

---

## 7. Personalized Risk Assessment

Personalized risk assessment maps fused allergen evidence to user-specific decision categories based on configured user profiles.

### Demonstrated Behavior (Demo Profile: WHEAT, SOY, MILK)

* **`food_ingredients.webp`**:
  - Overall Risk: **`HIGH`**
  - Mapped Allergens: WHEAT (`HIGH`), SOY (`HIGH`), MILK (`HIGH`)
  - Warning: *"Potentially relevant allergen detected for this user. Manual verification is recommended."*
* **`random.jpg`**:
  - Overall Risk: **`LOW`**
  - Mapped Allergens: WHEAT (`LOW`), SOY (`LOW`), MILK (`LOW`)
  - Warning: *"No known allergen detected from available evidence."*

**Important Clarification:** Personalized risk levels (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT_EVIDENCE`, `NO_MATCH`) are **deterministic system decision categories** based on matching logic and configured user allergy profiles. They are **not medical risk probabilities**, clinical safety guarantees, or diagnoses.

---

## 8. System Limitations

1. **Small Verified Evaluation Set:** Evaluation is restricted to 2 verified images (6 binary decisions), preventing statistically significant accuracy conclusions.
2. **Post-OCR Dependency:** The benchmark evaluates post-OCR processing using stored OCR text rather than fresh image-to-allergen predictions.
3. **OCR Typo Sensitivity:** Uncorrected OCR character glitches degrade candidate fuzzy matching scores.
4. **Blurry Image Degradation:** Blurry or poorly illuminated photographs (`oreo.jpg`) degrade OCR quality and prevent reliable ground-truth annotation.
5. **No Clinical Validation:** Predictions are rule-based string matching outputs, not clinically validated safety guarantees.
6. **No Cross-Contact Detection:** The system cannot detect unlisted facility cross-contamination or unlabelled allergens.
7. **Deterministic Categories:** Risk outputs are profile decision categories, not medical probabilities.

---

## 9. Future Work

1. **Expand Verified Benchmark Dataset:** Annotate a larger, diverse set of packaged food labels to enable statistical evaluation.
2. **Image Quality Pre-Filtering:** Implement automated blur and illumination checks to flag low-quality images prior to OCR.
3. **Fresh End-to-End OCR Benchmarking:** Rerun and evaluate updated OCR engines (e.g., PaddleOCR v4 / TrOCR) directly from raw images.
4. **Enhanced Post-OCR Formatting:** Add automated heuristics to repair missing whitespace and missing comma separators in OCR streams.
5. **Expand Knowledge Base:** Add additional allergen categories (e.g., PEANUTS, TREE NUTS, EGGS, FISH, SHELLFISH, SESAME) to the curated allergy knowledge base.
6. **Confidence Calibration:** Investigate probability calibration for fuzzy string matching and candidate segmentation scores.

---

## Generated Artifacts

- [`reports/end_to_end_evaluation.json`](file:///C:/sem5/edi/AllergyGuard/reports/end_to_end_evaluation.json)
- [`reports/end_to_end_evaluation.md`](file:///C:/sem5/edi/AllergyGuard/reports/end_to_end_evaluation.md)
- [`reports/error_analysis.json`](file:///C:/sem5/edi/AllergyGuard/reports/error_analysis.json)
- [`reports/error_analysis.md`](file:///C:/sem5/edi/AllergyGuard/reports/error_analysis.md)
- [`reports/evaluation_metrics.png`](file:///C:/sem5/edi/AllergyGuard/reports/evaluation_metrics.png)
- [`reports/evidence_status_summary.png`](file:///C:/sem5/edi/AllergyGuard/reports/evidence_status_summary.png)
