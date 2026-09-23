import re
from pathlib import Path

import pandas as pd

from .dataset_loader import load_ingredient_dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "knowledge"
    / "ingredient_vocabulary.csv"
)


# ---------------------------------------------------------
# Find ingredient column
# ---------------------------------------------------------

def find_ingredient_column(df: pd.DataFrame) -> str:

    possible_columns = [
        "ingredients",
        "ingredients_text",
        "ingredient",
        "ingredient_list",
        "ingredients_list",
    ]

    columns = {
        column.lower().strip(): column
        for column in df.columns
    }

    for candidate in possible_columns:

        if candidate in columns:
            return columns[candidate]

    raise ValueError(
        "Could not find ingredient column.\n"
        f"Available columns: {list(df.columns)}"
    )


# ---------------------------------------------------------
# Clean one ingredient term
# ---------------------------------------------------------

def clean_ingredient(text: str) -> str:

    if not text:
        return ""

    text = str(text).lower().strip()

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    # Remove percentages.
    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*%",
        " ",
        text
    )

    # Normalize common separators.
    text = text.replace(";", ",")

    # Remove leading/trailing punctuation.
    text = text.strip(" ,.;:-")

    # IMPORTANT:
    # Do NOT remove internal punctuation blindly.
    # This preserves word boundaries.

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ---------------------------------------------------------
# Split ingredient list
# ---------------------------------------------------------

def split_ingredients(text: str) -> list[str]:

    if not text:
        return []

    text = str(text)

    terms = []
    current = []

    # Track both round and square brackets.
    stack = []

    opening = {
        "(": ")",
        "[": "]",
    }

    closing = {
        ")": "(",
        "]": "[",
    }

    for char in text:

        # Opening bracket.
        if char in opening:
            stack.append(char)

        # Closing bracket.
        elif char in closing:

            if stack and stack[-1] == closing[char]:
                stack.pop()

        # Comma outside all brackets.
        if char == "," and not stack:

            term = "".join(current)

            term = clean_ingredient(term)

            if term:
                terms.append(term)

            current = []

        else:

            current.append(char)

    # Last term.
    term = "".join(current)

    term = clean_ingredient(term)

    if term:
        terms.append(term)

    return terms


# Parenthetical text on labels can either be a nested ingredient list or a
# description of the preceding ingredient.  Keep this list deliberately small:
# it prevents obvious label roles from becoming ingredients without attempting
# to maintain a second, hand-written ingredient vocabulary.
_EXPLANATORY_PARENTHETICALS = {
    "emulsifier",
    "preservative",
    "flavoring",
    "flavouring",
    "color",
    "colour",
    "stabilizer",
    "stabiliser",
    "thickener",
    "acidulant",
    "antioxidant",
    "processing aid",
}


def _top_level_groups(text: str) -> list[tuple[int, int, str]]:
    """Return balanced () and [] groups, including nested groups."""
    groups = []
    stack: list[tuple[str, int]] = []
    pairs = {")": "(", "]": "["}

    for index, char in enumerate(text):
        if char in "([":
            stack.append((char, index))
        elif char in pairs and stack and stack[-1][0] == pairs[char]:
            _, start = stack.pop()
            groups.append((start, index, text[start + 1:index]))

    return groups


def _is_explanatory_parenthetical(text: str) -> bool:
    """Recognize label annotations that should not become vocabulary terms."""
    cleaned = clean_ingredient(text)
    return (
        cleaned in _EXPLANATORY_PARENTHETICALS
        or cleaned.startswith("vitamin ")
        or cleaned.startswith("source of ")
    )


def extract_ingredient_terms(text: str) -> list[str]:
    """Recursively flatten an ingredient expression into ingredient-level terms.

    A parent phrase is retained, while nested comma-separated lists are expanded.
    Single explanatory parentheses, such as ``(emulsifier)`` and ``(vitamin c)``,
    are intentionally excluded.  Both round and square brackets are supported.
    """
    cleaned = clean_ingredient(text)
    if not cleaned:
        return []

    groups = _top_level_groups(cleaned)
    # A group with no enclosing group is directly attached to this ingredient.
    outer_groups = [
        group for group in groups
        if not any(other[0] < group[0] and group[1] < other[1] for other in groups)
    ]

    parent_parts = []
    cursor = 0
    for start, end, _ in outer_groups:
        parent_parts.append(cleaned[cursor:start])
        cursor = end + 1
    parent_parts.append(cleaned[cursor:])
    parent = clean_ingredient(" ".join(parent_parts))

    terms = [parent] if parent else []
    for _, _, inner_text in outer_groups:
        nested_items = split_ingredients(inner_text)
        if len(nested_items) == 1 and _is_explanatory_parenthetical(nested_items[0]):
            continue
        for nested_item in nested_items:
            terms.extend(extract_ingredient_terms(nested_item))

    # Retain order while avoiding duplicate terms caused by nested repetition.
    return list(dict.fromkeys(term for term in terms if term))


# ---------------------------------------------------------
# Remove obvious metadata
# ---------------------------------------------------------

def looks_like_ingredient(term: str) -> bool:

    if not term:
        return False

    # Ignore extremely long label text.
    if len(term) > 200:
        return False

    metadata_patterns = [

        r"\bdistributed\b",
        r"\bdistributed by\b",
        r"\bmanufactured by\b",
        r"\bmanufactured for\b",
        r"\bstore in\b",
        r"\bkeep refrigerated\b",
        r"\bkeep frozen\b",
        r"\bnet weight\b",
        r"\bsku\b",
        r"\bwww\.",
        r"\bhttps?://",
    ]

    for pattern in metadata_patterns:

        if re.search(
            pattern,
            term,
            flags=re.IGNORECASE
        ):
            return False

    return True


# ---------------------------------------------------------
# Build vocabulary
# ---------------------------------------------------------

def build_vocabulary(
    df: pd.DataFrame
) -> pd.DataFrame:

    ingredient_column = find_ingredient_column(df)

    print(
        f"\nUsing ingredient column: "
        f"{ingredient_column}"
    )

    frequency = {}

    for value in df[ingredient_column].dropna():

        for top_level_term in split_ingredients(value):
            terms = extract_ingredient_terms(top_level_term)

            for term in terms:

                if not looks_like_ingredient(term):
                    continue

                frequency[term] = (
                    frequency.get(term, 0) + 1
                )

    vocabulary = pd.DataFrame(
        [
            {
                "raw_term": term,
                "frequency": count,
            }
            for term, count in frequency.items()
        ]
    )

    if vocabulary.empty:
        raise ValueError(
            "No ingredient terms were extracted."
        )

    vocabulary = vocabulary.sort_values(
        by=["frequency", "raw_term"],
        ascending=[False, True]
    )

    vocabulary = vocabulary.reset_index(drop=True)

    return vocabulary


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

def save_vocabulary(
    vocabulary: pd.DataFrame
) -> None:

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    vocabulary.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        f"\nVocabulary saved to:\n"
        f"{OUTPUT_PATH}"
    )

    print(
        f"Unique ingredient terms: "
        f"{len(vocabulary)}"
    )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("BUILDING INGREDIENT VOCABULARY")
    print("=" * 70)

    df = load_ingredient_dataset()

    vocabulary = build_vocabulary(df)

    save_vocabulary(vocabulary)

    print("\nSample vocabulary:")

    print(
        vocabulary.head(30).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
