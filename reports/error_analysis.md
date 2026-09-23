# AllergyGuard Error Analysis & Uncertainty Report

## 1. Error Analysis Overview
This report classifies observed system behavior, OCR corruption artifacts, fuzzy-matching uncertainty, and dataset annotation boundaries across the AllergyGuard evaluation dataset. The analysis evaluates intermediate representations without manufacturing artificial error categories.

## 2. Dataset Scope
- **Verified Evaluation Samples (2):** `food_ingredients.webp`, `random.jpg`
- **Uncertain Samples (1):** `oreo.jpg` (held out from quantitative metrics)
- **Excluded Samples (2):** `restaurant.jpg`, `test_image.jpg` (non-packaged / non-ingredient text)
- **Evaluated Allergens:** WHEAT, SOY, MILK

## CASE 1 SOY LEOTAIN
- **Input / Raw Term:** `SOY LEOTAIN`
- **Category:** OCR spelling corruption / Fuzzy-match uncertainty
- **Observed Status:** OBSERVED
- **Raw Evidence:** OCR term 'SOY LEOTAIN' matched dataset candidate 'soy lecithin' with confidence 0.7774.
- **System Behavior:** Normalized term='soy lecithin' with match_type='dataset_candidate', confidence=0.7774, status='candidate'. Evidence fusion assigned evidence_type='FUZZY_NORMALIZATION' (status='weak') resulting in AllergenAssessment status='POTENTIAL'.
- **Interpretation:** The system correctly refrained from treating the corrupted term as a confirmed exact match. Because status='candidate' (confidence < 0.95), the evidence fusion layer produces status='POTENTIAL' rather than 'DETECTED'. Under strict exact-detection metrics, this term is not automatically accepted as positive, preventing false-positive allergen detection from corrupted text.
- **System Limitation:** Corrupted OCR spelling cannot be resolved with 100% confidence without human review or secondary OCR verification.

## CASE 2 ONION SUNFLOWER OIL
- **Input / Raw Term:** `ONION SUNFLOWER OIL`
- **Category:** Ambiguous ingredient / Partial normalization
- **Observed Status:** OBSERVED
- **Raw Evidence:** Unseparated OCR token string 'ONION SUNFLOWER OIL' evaluated by candidate segmenter.
- **System Behavior:** Candidate segmentation recognized segment 'sunflower oil' (similarity=1.0) while preserving unresolved_text='ONION SUNFLOWER OIL'. Status='ambiguous', match_type='partial_match'. No allergen mapping was invented for 'onion'.
- **Interpretation:** The system correctly recognized 'sunflower oil' as a partial segment while marking the overall term as ambiguous. It conservatively avoided hallucinating a synthetic canonical ingredient mapping for 'onion'. Furthermore, sunflower oil is not mapped to any allergen in the curated allergy knowledge base.
- **System Limitation:** OCR token concatenation (missing comma separator) creates unsegmented text fragments that require candidate segmentation.

## CASE 3 CONTAINS STATEMENT
- **Input / Raw Term:** `CONTAINS: WHEAT, SOY, MILK`
- **Category:** Explicit label allergen claim
- **Observed Status:** OBSERVED
- **Raw Evidence:** OCR label text contained explicit statement 'CONTAINS: WHEAT, SOY, MILK'.
- **System Behavior:** Extracted 3 AllergenEvidence items with evidence_type='CONTAINS_STATEMENT', source='label_contains_statement', confidence=1.0, status='strong'. Fusion assigned status='DETECTED' for MILK, SOY, WHEAT.
- **Interpretation:** Direct CONTAINS statements on package labels represent explicit manufacturer allergen disclosures. The evidence-fusion layer assigns them maximum confidence (1.0) and status='strong', ensuring they receive higher precedence than uncertain fuzzy ingredient matches.
- **System Limitation:** Relies on OCR accurately capturing label CONTAINS text regions.

## CASE 4 SOYBEAN OIL
- **Input / Raw Term:** `SOYBEAN OIL`
- **Category:** Curated allergen knowledge mapping
- **Observed Status:** OBSERVED
- **Raw Evidence:** Term 'SOYBEAN OIL' in ingredient list.
- **System Behavior:** Normalized to canonical_concept='soy', allergen='SOY' via match_type='curated_exact', status='known', confidence=1.0. Evidence status='strong' led to AllergenAssessment status='DETECTED'.
- **Interpretation:** Curated allergy knowledge explicitly maps 'soybean oil' to the SOY allergen canonical concept. This mapping is deterministic and traceable back to the curated allergen dictionary, generating strong evidence.
- **System Limitation:** Deterministic knowledge mapping requires curated dictionary coverage for all major allergen derivatives.

## CASE 5 NESTED MILK
- **Input / Raw Term:** `SEMISWEET CHOCOLATE CHIPS (... MILK)`
- **Category:** Hierarchical ingredient extraction & evidence fusion
- **Observed Status:** OBSERVED
- **Raw Evidence:** Sub-ingredient 'MILK' inside parenthetical structure of 'SEMISWEET CHOCOLATE CHIPS'.
- **System Behavior:** Hierarchical extractor identified nested level='nested', parent='SEMISWEET CHOCOLATE CHIPS'. Evidence fusion assigned evidence_type='NESTED_INGREDIENT' with status='strong', yielding AllergenAssessment MILK status='DETECTED'.
- **Interpretation:** Hierarchical ingredient extraction preserves parent-child relationships and prevents nested terms from being lost. Evidence fusion treats valid nested allergen terms as strong evidence for allergen detection.
- **System Limitation:** Requires well-formed parenthetical or bracketed ingredient list structures in OCR text.

## CASE 6 OREO UNCERTAIN
- **Input / Raw Term:** `oreo.jpg`
- **Category:** Ground-truth & OCR uncertainty
- **Observed Status:** OBSERVED
- **Raw Evidence:** Image oreo.jpg has PaddleOCR average confidence = 0.5954 and UNCERTAIN ground truth annotation.
- **System Behavior:** Excluded from quantitative metrics calculation in evaluation set loader (get_verified_samples).
- **Interpretation:** Low OCR confidence (0.5954) reflects poor image legibility (blurry photograph). Crucially, low OCR confidence indicates quality degradation rather than proof of OCR error or accuracy. The sample is appropriately held out as UNCERTAIN until manual inspection or higher-quality re-imaging is available.
- **System Limitation:** Blurry or poorly illuminated photographs degrade OCR text extraction quality, requiring manual verification.

## 9. Error Category Summary
The table below categorizes the 10 standard evaluation failure modes against empirical project evidence:

| Category | Status | Evidence |
|---|---|---|
| OCR error | **OBSERVED** | Observed in food_ingredients.webp ('CHOCOLATÉ' character glitch) and oreo.jpg (low OCR confidence 0.5954 with garbled text). |
| Ingredient extraction error | **OBSERVED** | Observed in random.jpg where 'ONION SUNFLOWER OIL' was merged without a comma in the raw OCR stream. |
| OCR spacing error | **OBSERVED** | Observed in random.jpg ('SUNFLOWERAND/ OR' missing space; missing space after commas in list items). |
| Normalization exact-match failure | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | All valid, non-corrupted ingredient terms in verified samples matched curated or dataset index entries exactly. |
| Fuzzy-match uncertainty | **OBSERVED** | Demonstrated by corrupted typo variant 'SOY LEOTAIN' matching 'soy lecithin' at candidate status (confidence 0.7774). |
| Ambiguous ingredient | **OBSERVED** | Observed in 'ONION SUNFLOWER OIL' yielding candidate segmentation partial match with ambiguous status. |
| Unknown ingredient | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | No valid ingredient in the verified sample set was left completely unmapped or unknown. |
| Allergen knowledge gap | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | Curated allergen dictionary cleanly covered all present target allergens (WHEAT, SOY, MILK). |
| Evidence conflict | **NOT_OBSERVED_IN_CURRENT_SAMPLES** | No contradictory label statements (e.g. CONTAINS vs ingredient list) were present in the verified dataset. |
| Ground-truth ambiguity | **OBSERVED** | Observed in oreo.jpg, where photograph blurriness prevented reliable human manual ground-truth annotation. |

## 10. System Limitations
- Post-OCR processing quality depends heavily on clean OCR input text; OCR typos degrade fuzzy matching confidence.
- Candidate fuzzy matches below high-confidence thresholds (0.95) are marked as POTENTIAL and require manual verification.
- Unsegmented OCR token strings (e.g. missing commas) rely on candidate segmentation and partial matching.
- Blurry or poorly illuminated label photographs (e.g. oreo.jpg) degrade OCR confidence and prevent reliable manual annotation.
- System predictions are deterministic matching outputs, not medical risk scores, diagnoses, or safety guarantees.

## 11. Implications for Future Work
- Expand curated allergen and ingredient dictionaries to reduce dependence on candidate fuzzy matching.
- Incorporate image quality pre-filtering to automatically flag blurry photographs prior to OCR processing.
- Enhance OCR post-processing heuristics to handle missing whitespace and missing comma separators.
- Gather a larger, multi-label verified benchmark dataset to enable statistically rigorous evaluation metrics.
