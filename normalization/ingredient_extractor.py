import re
from typing import List, Optional

from .schemas import IngredientEvidence

def _strip_packaging_metadata(text: str) -> str:
    """Remove packaging/distribution metadata from ingredient text."""

    if not text:
        return ""

    boundary_patterns = [
        r"\bDIST\.\s*&\s*SOLD\b",
        r"\bDISTRIBUTED\s+BY\b",
        r"\bSOLD\s+EXCLUSIVELY\b",
        r"\bSTORE\s+IN\s+A\s+COOL\b",
        r"\bKEEP\s+REFRIGERATED\b",
        r"\bKEEP\s+FROZEN\b",
        r"\bNET\s+WT\b",
        r"\bSKU\s*#",
    ]

    boundary_matches = []

    for pattern in boundary_patterns:
        boundary = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if boundary:
            boundary_matches.append(boundary)

    if boundary_matches:
        earliest = min(
            boundary_matches,
            key=lambda match: match.start()
        )

        text = text[:earliest.start()]

    return text.strip()

def extract_ingredient_section(text: str) -> str:
    """
    Extract text after INGREDIENTS and before CONTAINS
    or obvious packaging metadata.
    """
    if not text:
        return ""

    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()

    match = re.search(
        r"\bINGREDIENTS?\s*:\s*",
        text,
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    section = text[match.end():]

    contains_match = re.search(
        r"\bCONTAINS?\s*:",
        section,
        flags=re.IGNORECASE
    )

    if contains_match:
        section = section[:contains_match.start()]

    section = _strip_packaging_metadata(section)

    return section.strip()


def repair_ocr_brackets(text: str) -> str:
    """Repair common OCR substitutions involving brackets without changing meaning."""
    if not text:
        return ""

    return text.replace("{", "(").replace("}", ")")


def clean_ingredient_text(text: str) -> str:
    """Basic cleanup of OCR noise while preserving ingredient content."""
    if not text:
        return ""

    text = text.replace("\n", " ")
    text = repair_ocr_brackets(text)

    # Remove OCR-captured nutrition percentages.
    text = re.sub(
        r"\b\d+\s*%",
        "",
        text
    )

    # Remove OCR-captured standalone gram quantities.
    text = re.sub(
        r"\b\d+\s*g\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b\d+\s*g\s+\d+\s*%",
        " ",
        text,
        flags=re.IGNORECASE
    )

    # Repair OCR words that have been joined together.
    text = re.sub(
        r"(?i)enriched\s*(?:f\s*l\s*o\s*u\s*r|flour)",
        "ENRICHED FLOUR",
        text
    )

    text = re.sub(
        r"(?i)chocolate\s*(?:c\s*h\s*i\s*p\s*s|chips)",
        "CHOCOLATE CHIPS",
        text
    )

    # Repair common OCR accent substitution.
    text = re.sub(
        r"(?i)\bchocolaté\b",
        "CHOCOLATE",
        text
    )

    text = re.sub(
        r"(?i)\bcottonseed\b(?:\s+\d+[A-Z0-9/]+)*"
        r"(?:\s+\d+\s*g)?\s+\boil\b",
        "COTTONSEED OIL",
        text
    )

    # Repair OCR spacing in alternative oil statements.
    text = re.sub(
        r"(?i)\bsunflowerand/\s*or\s*safflower\s+and/\s*or\s+canola\s+oil\b",
        "SUNFLOWER AND/OR SAFFLOWER AND/OR CANOLA OIL",
        text
    )

    # Remove common OCR-inserted date/packaging text before an ingredient.
    text = re.sub(
        r"(?i)\bplease\s+see\s+date\s+printed\s+",
        "",
        text
    )

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip(" ,.;:")

def _split_on_commas_outside_parens(text: str) -> List[str]:
    """
    Split on commas when not inside parentheses,
    while tolerating malformed OCR.
    """
    if not text:
        return []

    segments: List[str] = []
    current: List[str] = []
    depth = 0

    for char in text:
        if char == "(":
            depth += 1

        elif char == ")":
            if depth > 0:
                depth -= 1

        if char == "," and depth == 0:
            term = "".join(current).strip()

            if term:
                segments.append(term)

            current = []

        else:
            current.append(char)

    final_term = "".join(current).strip()

    if final_term:
        segments.append(final_term)

    return segments


def _clean_term(raw_term: str) -> str:
    cleaned = clean_ingredient_text(raw_term)

    cleaned = re.sub(
        r"^\s*[-•*]+\s*",
        "",
        cleaned
    )

    cleaned = cleaned.strip(" ,.;:")

    return cleaned


def _strip_packaging_prefix(raw_parent: str) -> str:
    """
    Remove common OCR packaging metadata while preserving
    the actual ingredient phrase.
    """
    if not raw_parent:
        return ""

    text = raw_parent.strip()

    patterns = [
        r"^(?:FOR\s+BEST\s+WHEN\s+USED\s+BY\s+|BEST\s+WHEN\s+USED\s+BY\s+|FOR\s+BEST\s+BY\s+|USE\s+BY\s+|BEST\s+BY\s+)\s*(?:\d+\s*%\s*)?",
        r"^(?:PACKED\s+ON\s+|SELL\s+BY\s+|BEST\s+BEFORE\s+|EXP\s*\.\s*|EXPIRATION\s+DATE\s+)",
        r"^\d+\s*%\s*",
    ]

    for pattern in patterns:
        new_text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

        if new_text != text:
            text = new_text
            break

    return text.strip(" ,.;:")


def _parse_parenthetical_term(
    raw_term: str,
    parent: Optional[str] = None,
    source: str = "paddleocr",
    original_raw_text: Optional[str] = None,
) -> List[IngredientEvidence]:
    """
    Create parent-child ingredient evidence from a single OCR candidate.
    """
    if not raw_term:
        return []

    cleaned = _clean_term(raw_term)

    if not cleaned:
        return []

    evidence: List[IngredientEvidence] = []

    open_idx = cleaned.find("(")

    if open_idx >= 0:

        parent_name = _strip_packaging_prefix(
            cleaned[:open_idx].strip()
        )

        if not parent_name:
            parent_name = parent

        if parent_name:
            evidence.append(
                IngredientEvidence(
                    source=source,
                    raw_text=original_raw_text or raw_term,
                    cleaned_text=parent_name,
                    parent=parent,
                    level="top_level" if parent is None else "nested",
                    extraction_method="nested_parentheses",
                )
            )

        close_idx = cleaned.rfind(")")
        has_balanced_parens = close_idx > open_idx

        # Handle malformed/unclosed parentheses
        if not has_balanced_parens:

            inner_text = cleaned[open_idx + 1:].strip()

            if inner_text:

                for nested_text in _split_on_commas_outside_parens(
                    inner_text
                ):
                    nested_clean = _clean_term(nested_text)

                    if not nested_clean:
                        continue

                    if "(" in nested_clean:
                        evidence.extend(
                            _parse_parenthetical_term(
                                nested_clean,
                                parent=parent_name or parent,
                                source=source,
                            )
                        )

                    else:
                        evidence.append(
                            IngredientEvidence(
                                source=source,
                                raw_text=nested_text,
                                cleaned_text=nested_clean,
                                parent=parent_name or parent,
                                level="nested",
                                extraction_method="nested_parentheses",
                            )
                        )

            return evidence

        inner_text = cleaned[
            open_idx + 1:close_idx
        ].strip()

        if inner_text:

            for nested_text in _split_on_commas_outside_parens(
                inner_text
            ):
                nested_clean = _clean_term(nested_text)

                if not nested_clean:
                    continue

                if "(" in nested_clean:
                    evidence.extend(
                        _parse_parenthetical_term(
                            nested_clean,
                            parent=parent_name or parent,
                            source=source,
                        )
                    )

                else:
                    evidence.append(
                        IngredientEvidence(
                            source=source,
                            raw_text=nested_text,
                            cleaned_text=nested_clean,
                            parent=parent_name or parent,
                            level="nested",
                            extraction_method="nested_parentheses",
                        )
                    )

        return evidence

    evidence.append(
        IngredientEvidence(
            source=source,
            raw_text=raw_term,
            cleaned_text=cleaned,
            parent=parent,
            level="top_level" if parent is None else "nested",
            extraction_method="comma_split",
        )
    )

    return evidence


def hierarchical_extract_ingredients(
    text: str,
    image: Optional[str] = None,
    source: str = "paddleocr"
) -> List[IngredientEvidence]:
    """
    Extract ingredient evidence while preserving:

    - raw OCR text
    - cleaned candidate text
    - parent-child provenance
    - extraction method
    - image provenance

    Also expands AND/OR ingredient alternatives such as:

    SUNFLOWER AND/OR SAFFLOWER AND/OR CANOLA OIL

    into:

    SUNFLOWER OIL
    SAFFLOWER OIL
    CANOLA OIL
    """

    if text is None:
        return []

    text = str(text).strip()

    if not text or text.lower() == "nan":
        return []

    section = extract_ingredient_section(text)

    # Support already-extracted ingredient text that does not
    # contain an INGREDIENTS: heading.
    if not section and not re.search(
        r"\bCONTAINS?\s*:",
        text,
        flags=re.IGNORECASE
    ):
        section = _strip_packaging_metadata(text)

    if not section:
        return []

    cleaned_section = clean_ingredient_text(section)

    if not cleaned_section:
        return []

    evidence: List[IngredientEvidence] = []

    # First split the ingredient list using commas outside parentheses.
    terms = _split_on_commas_outside_parens(cleaned_section)
    raw_terms = _split_on_commas_outside_parens(section)

    # Expand AND/OR alternatives.
    expanded_terms: List[tuple[str, str]] = []

    for term_index, term in enumerate(terms):
        raw_term = raw_terms[term_index] if term_index < len(raw_terms) else term

        if re.search(
            r"\s+AND/OR\s+",
            term,
            flags=re.IGNORECASE
        ):
            alternatives = re.split(
                r"\s+AND/OR\s+",
                term,
                flags=re.IGNORECASE
            )

            # In statements such as:
            # SUNFLOWER AND/OR SAFFLOWER AND/OR CANOLA OIL
            #
            # "OIL" appears only on the final alternative.
            # Attach it to the other alternatives as well.
            if (
                alternatives
                and alternatives[-1].strip().upper().endswith("OIL")
            ):
                alternatives[-1] = re.sub(
                    r"\s+OIL$",
                    "",
                    alternatives[-1],
                    flags=re.IGNORECASE
                )

                alternatives = [
                    alt.strip() + " OIL"
                    for alt in alternatives
                ]

            expanded_terms.extend((alternative, raw_term) for alternative in alternatives)

        else:
            expanded_terms.append((term, raw_term))

    # Process each individual ingredient.
    for term, raw_term in expanded_terms:

        cleaned_term = _clean_term(term)

        if not cleaned_term:
            continue

        for item in _parse_parenthetical_term(
            term,
            source=source,
            original_raw_text=raw_term,
        ):
            item.image = image
            evidence.append(item)

    # Deduplicate while preserving order.
    dedup: List[IngredientEvidence] = []
    seen = set()

    for item in evidence:

        key = (
            item.raw_text,
            item.cleaned_text,
            item.parent,
            item.level,
            item.extraction_method,
        )

        if key not in seen:
            seen.add(key)
            dedup.append(item)

    return dedup


def split_top_level_ingredients(text: str) -> List[str]:
    """Backward-compatible flat extractor used by legacy callers."""
    if not text:
        return []

    section = clean_ingredient_text(text)

    return _split_on_commas_outside_parens(section)


def extract_nested_ingredients(text: str) -> List[str]:
    """Backward-compatible nested extraction helper."""
    items = hierarchical_extract_ingredients(text)

    return [
        item.cleaned_text
        for item in items
        if item.level == "nested"
    ]


def extract_ingredients(text: str) -> List[str]:
    """Main ingredient extraction pipeline, returning flat legacy strings."""
    evidence = hierarchical_extract_ingredients(text)

    return [
        item.cleaned_text
        for item in evidence
        if item.cleaned_text
    ]
