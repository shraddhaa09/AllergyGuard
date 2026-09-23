# AllergyGuard

AllergyGuard processes packaged-food labels into traceable ingredient and
allergen evidence. Current architecture:

`Image → OCR → Ingredient Extraction → Ingredient Normalization → Allergy Knowledge → Evidence Fusion → Personalized Risk Assessment → Explainable Result`

Each layer has a separate responsibility. Dataset vocabulary expands ingredient
coverage; curated knowledge supplies allergen relationships; evidence fusion
aggregates label evidence; the risk layer applies a supplied user profile.

## Personalized risk categories

`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT_EVIDENCE`, and `NO_MATCH` are
deterministic system decision categories, not medical probabilities or clinical
advice. `HIGH` requires a profile allergen with detected evidence; `MEDIUM`
requires potential evidence; `LOW` requires an explicit `NOT_DETECTED`
assessment; and incomplete evidence remains `INSUFFICIENT_EVIDENCE`.

Detected evidence takes precedence over weaker conflicting assessments. The
system preserves the contributing ingredient, evidence type, confidence,
provenance, source, and partial/unresolved text for presentation.

No result means a product is safe, allergen-free, or medically appropriate.
Matching confidence is not calibrated probability, and the project does not
predict reactions, cross-contact, or clinical severity.

Run the pipeline with `python -m normalization.pipeline`. Its built-in profile
is explicitly a demonstration only; applications should supply a user profile
from their own UI, API, or account system.
