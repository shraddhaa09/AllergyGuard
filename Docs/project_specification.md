# AllergyGuard: Confidence-Aware Multimodal Food-Allergy Risk Assessment

**Project Specification**

> Status note: All sections below reflect decisions actually discussed and locked. Where something is still a proposal rather than a confirmed decision, it is marked explicitly. Nothing here should be read as an implemented or validated result — this is a design specification, not a results report.

---

## 1. Problem Statement

Food-allergy risk assessment from food images is difficult because **allergens are often not directly visible in the image**. A food may look safe while containing hidden ingredients, and visually similar foods may have different compositions. For example, a pizza may visually appear to contain cheese while actually using a cheese substitute, or a product may contain an allergen that cannot be identified from its appearance.

Existing food-recognition and ingredient-recognition approaches generally focus on individual tasks such as food classification, ingredient recognition, or OCR. They do not adequately address the problem of combining heterogeneous evidence from food images, ingredient text, and structured food-allergen knowledge while handling uncertainty and conflicting evidence.

We propose a multimodal food-allergy risk assessment system that combines **vision, OCR, ingredient normalization, a food-allergen knowledge graph, and adaptive evidence fusion** to produce a confidence-aware, personalized allergy-risk assessment with an explanation of the evidence used.

**Reframing the question:**

Not: *"Can AI recognize a pizza?"*
But: *"Can AI make a reliable allergy-risk assessment from incomplete and potentially conflicting visual and textual food evidence?"*

---

## 2. Research Gap

We are **not** claiming that no one has ever combined these technologies — that would require a full systematic literature review to substantiate. The defensible gap is narrower.

Existing approaches commonly address individual components in isolation: food recognition, ingredient recognition, OCR, allergen identification, food knowledge bases. What is missing is a **systematic multimodal decision framework** that:

1. Combines visual and textual evidence
2. Maps extracted ingredients to structured allergen knowledge
3. Explicitly handles conflicting or incomplete evidence
4. Represents uncertainty instead of forcing a binary decision
5. Incorporates the user's allergy profile into the final risk assessment

**Core research direction:** Confidence-aware multimodal evidence fusion for personalized food-allergy risk assessment.

**Open item (not yet locked):** The claim "no existing paper does this" cannot be written into the paper until a literature review identifies and rules out the closest prior work. This is the next research step before implementation.

---

## 3. Research Questions

| # | Question | Tests |
|---|----------|-------|
| RQ1 | Does combining visual and textual evidence improve allergen identification compared with using a single evidence source? | Vision vs. OCR vs. Vision+OCR |
| RQ2 | Does knowledge-guided evidence fusion improve reliability when multimodal evidence is incomplete or conflicting? | FoodOn + Adaptive Evidence Fusion Engine + Confidence & Conflict Analysis |
| RQ3 | Can confidence and conflict analysis reduce overconfident predictions under uncertain or conflicting evidence? | Confidence & Conflict Analysis module |
| RQ4 | Can the system adapt the final risk assessment according to the user's allergy profile? | Personalized Risk Assessment module |

---

## 4. Proposed Architecture

```
                    User Image
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
       Vision Models             OCR
              │                   │
              ▼                   ▼
      Food / Visible         Ingredient Text
       Ingredients                 │
              │                   │
              └─────────┬─────────┘
                        ▼
             Ingredient Normalization
                        │
                        ▼
              FoodOn / Knowledge Base
                        │
                        ▼
        Adaptive Evidence Fusion Engine
                        │
                        ▼
          Confidence & Conflict Analysis
                        │
                        ▼
           Personalized Risk Assessment
                        │
                        ▼
              Explainable Report
```

**Component roles:**

- **Vision** — identifies food and visually observable information.
- **OCR** — extracts ingredient/label text when available.
- **Ingredient Normalization** — converts variants and OCR errors into standardized ingredient concepts (e.g., `Casein` / `Caseln` / `Milk casein` → standardized `Casein` → related to `Milk`).
- **FoodOn / Knowledge Base** — provides structured semantic relationships between foods, ingredients, and related concepts.
- **Adaptive Evidence Fusion Engine** — combines evidence from multiple sources rather than trusting one source blindly.
- **Confidence & Conflict Analysis** — determines evidence strength and flags disagreements.
- **Personalized Risk Assessment** — compares evidence against the user's allergy profile.
- **Explainable Report** — shows the user what was detected, what evidence supports it, where uncertainty exists, and the resulting risk assessment.

---

## 5. Locked Models & Tools

### Vision
- **Florence-2** — multimodal visual understanding, extracting information from food images.
- **Qwen2-VL** — second, independent vision-language model providing an alternate visual interpretation.

*Rationale for two models:* multiple independent visual evidence sources rather than reliance on a single model — important for later evidence-fusion experiments. Neither model is being trained from scratch.

### OCR
- **PaddleOCR** — locked.
  ```
  Food/package image → PaddleOCR → Ingredient / label text
  ```

### Ingredient Normalization
Approaches discussed:
1. Dictionary + synonym mapping
2. RapidFuzz for approximate matching
3. FoodOn-based semantic reasoning

Embedding-based semantic search was discussed but **deliberately not made a core requirement** — the research contribution is the evidence-fusion framework, not accumulating every possible NLP technique.

### Knowledge Base
- **FoodOn** — locked as the main ontology/knowledge resource.
- **OpenFoodFacts** and **USDA FoodData Central** — supporting structured food information sources.

### Research Components (our own methodology, not pretrained models)
- Adaptive Evidence Fusion Engine
- Confidence & Conflict Analysis
- Personalized Risk Assessment
- Explainable Report

---

## 6. Dataset Strategy

We are not building everything from scratch — we use existing public resources plus a small curated evaluation benchmark.

| Source | Role |
|---|---|
| **Food-101** | Food recognition evaluation only. Does *not* provide sufficient allergen information — Food-101 ≠ our complete allergy dataset. |
| **OpenFoodFacts** | Product images, ingredient lists, allergen declarations, product information — most directly relevant to our pipeline. |
| **FoodOn** | Ontology (not an image dataset) — semantic food concepts, relationships, structured knowledge. |
| **USDA FoodData Central** | Supporting food-information/knowledge resource, not primary evaluation data. |
| **Our curated benchmark** | "AllergyGuard Multimodal Evaluation Benchmark" — for evaluation only, not for large-scale training. |

---

## 7. Benchmark Design

Proposed target: **~200 carefully selected cases**, subject to availability and ground-truth quality. These figures are our proposed design, not statistics from an existing dataset, and should be adjusted if reliable ground truth cannot be obtained.

| Category | Approx. target |
|---|---:|
| Packaged food with clear labels | 80 |
| Difficult/poor labels | 30 |
| Restaurant/served food | 30 |
| Homemade food | 20 |
| Vegan/substitute foods | 15 |
| Multiple-allergen foods | 15 |
| Precautionary-label cases | 10 |
| **Total** | **200** |

### Challenge sets

1. **Multimodal agreement** — vision and OCR agree.
2. **Multimodal conflict** — e.g., vision → cheese pizza, OCR → vegan cheese, knowledge → no milk evidence. System should flag disagreement rather than pick one silently.
3. **OCR noise** — e.g., ground truth `Casein`, OCR output `Caseln`; normalization should recover the correct ingredient.
4. **Unknown/insufficient evidence** — e.g., homemade dish with no label; system should be able to output "insufficient evidence" rather than guess.
5. **Personalized risk** — same underlying food evidence (e.g., milk detected), different outcomes for User A (milk allergy) vs. User B (peanut allergy).

---

## 8. Evaluation Metrics

A single accuracy number is not adequate across modules; each module needs metrics appropriate to its task.

| Module | Metrics |
|---|---|
| Vision | Accuracy, Top-1 accuracy, Top-5 accuracy |
| Ingredient Normalization | Precision, Recall, F1-score, Exact Match where appropriate |
| Allergen Detection | Multi-label Precision, Recall, F1 (a food can have multiple allergens, so simple accuracy is insufficient) |
| Confidence | Expected Calibration Error (ECE), Brier Score |
| Conflict Detection | Precision, Recall, F1 (for identifying disagreement between evidence sources) |
| Personalized Risk | Accuracy, Macro-F1, Confusion matrix — evaluated against predefined benchmark rules, **not** claimed as clinical validation |
| Explainability | Manual evaluation on a subset: correct reference to evidence, correct representation of knowledge relationships, avoidance of unsupported claims, correct explanation of conflicts/uncertainty |

---

## 9. Research Contribution

Novelty is **not** claimed on the basis of using existing pretrained models (Florence-2, Qwen2-VL, PaddleOCR, FoodOn are all existing building blocks). The intended contribution is the framework built around them:

> A confidence-aware multimodal evidence-fusion framework for personalized food-allergy risk assessment that integrates visual evidence, OCR-derived ingredient evidence, structured food-allergen knowledge, and user-specific allergy information — while explicitly representing conflicting and insufficient evidence.

Specific intended contributions:

1. **Multimodal evidence integration** — Vision + OCR + Knowledge, rather than a single modality.
2. **Conflict-aware reasoning** — the system does not assume every evidence source is correct.
3. **Confidence-aware output** — distinguishes strong evidence from uncertain evidence.
4. **Personalized risk assessment** — same food, different risk output per allergy profile.
5. **Explainable decision path** — the user can see why the system reached its conclusion.
6. **Evaluation benchmark** — a curated set of difficult cases for realistic evaluation.

**Caveat:** these are *intended* contributions. They become actual research contributions only after experiments demonstrate meaningful advantages over appropriate baselines.

---

## 10. Limitations

1. **Visual ambiguity** — an image cannot reliably reveal every ingredient (e.g., cannot prove whether pizza cheese is dairy-based or plant-based from appearance alone).
2. **Hidden ingredients** — some allergens are not visually detectable at all.
3. **OCR errors** — poor lighting, curved packaging, blur, unusual fonts, and multilingual labels can cause extraction errors.
4. **Knowledge-base incompleteness** — FoodOn or supporting resources may lack certain ingredients/relationships. "Not found in knowledge base" must be treated as **unknown**, not **negative**.
5. **Dataset bias** — public food datasets may overrepresent certain cuisines, countries, food categories, or packaging styles, limiting generalization.
6. **Ground-truth limitations** — reliable ingredient information for restaurant and homemade food is hard to obtain; uncertain cases should not be forced into artificial ground truth.
7. **No clinical validation** — this is a research prototype. The system must not claim to medically diagnose allergies or replace a physician/allergist. Output is a decision-support risk assessment, not a diagnosis.
8. **Model dependency** — errors in Florence-2, Qwen2-VL, or PaddleOCR propagate downstream.
9. **Knowledge reasoning limitations** — food relationships are not always deterministic (e.g., "cheese" does not guarantee a fixed allergen relationship across every substitute product) — which is precisely why evidence and uncertainty handling matter.

---

## 11. End-to-End Research Flow

```
                    PROBLEM
                       │
                       ▼
       Food appearance ≠ complete ingredient truth
                       │
                       ▼
                RESEARCH GAP
                       │
                       ▼
       Multimodal + Knowledge + Uncertainty
                       │
                       ▼
                  OUR SYSTEM
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Florence-2     Qwen2-VL      PaddleOCR
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              Ingredient Normalization
                       ▼
                    FoodOn
                       ▼
             Evidence Fusion 
                       ▼
             Conflict + Confidence
                       ▼
             Personalized Risk
                       ▼
              Explainable Report
                       │
                       ▼
              BENCHMARK EVALUATION
                       │
                       ▼
          Baselines + Ablation Studies
                       │
                       ▼
             Research Conclusions
```

---

## 12. Open Items / Not Yet Locked

- **Literature-supported research gap validation.** The current gap statement is a strong candidate direction but has not been checked against the closest existing papers. This must be done before any "novel" or "first" language is used in the paper, and is the immediate next step before implementation begins.