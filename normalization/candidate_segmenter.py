from dataclasses import dataclass
from typing import List

from .normalizer import clean_text, EXACT_INDEX


@dataclass
class SegmentCandidate:
    text: str
    normalized_term: str | None
    confidence: float
    status: str
    start: int
    end: int


def compact_text(text: str) -> str:
    """
    Remove whitespace for OCR-tolerant comparison.

    Example:
        "semisweet chocolate chips"
        -> "semisweetchocolatechips"

        "semisweetchocolate chips"
        -> "semisweetchocolatechips"
    """
    return "".join(text.split())


def generate_candidate_segments(text: str) -> List[SegmentCandidate]:
    """
    Find the longest non-overlapping known ingredient concepts
    inside an OCR phrase.

    The function does NOT invent missing ingredients.

    Examples:

        RICE FLOUR SEA SALT

    becomes:

        RICE FLOUR -> rice flour
        SEA SALT   -> salt

    And:

        ONION SUNFLOWER OIL

    becomes:

        SUNFLOWER OIL -> sunflower oil

    leaving ONION unresolved.

    OCR spacing variations are also supported. For example:

        SEMISWEETCHOCOLATE CHIPS

    can match:

        SEMISWEET CHOCOLATE CHIPS
    """

    if not text or not text.strip():
        return []

    # Use the existing generic text-cleaning logic.
    cleaned = clean_text(text)

    if not cleaned:
        return []

    words = cleaned.split()

    candidates: List[SegmentCandidate] = []

    position = 0

    while position < len(words):

        best_match = None

        # Search from the longest possible phrase
        # to the shortest phrase.
        for end in range(len(words), position, -1):

            phrase = " ".join(words[position:end])

            # -------------------------------------------------
            # 1. Exact dictionary match
            # -------------------------------------------------

            if phrase in EXACT_INDEX:

                info = EXACT_INDEX[phrase]

                best_match = SegmentCandidate(
                    text=phrase,
                    normalized_term=info["canonical"],
                    confidence=1.0,
                    status="known",
                    start=position,
                    end=end,
                )

                break

            # -------------------------------------------------
            # 2. OCR spacing variation
            # -------------------------------------------------

            compact_phrase = compact_text(phrase)

            for known_term, info in EXACT_INDEX.items():

                if compact_text(known_term) == compact_phrase:

                    best_match = SegmentCandidate(
                        text=phrase,
                        normalized_term=info["canonical"],
                        confidence=0.95,
                        status="known_spacing_variation",
                        start=position,
                        end=end,
                    )

                    break

            if best_match:
                break

        # -----------------------------------------------------
        # Accept the best match and move forward.
        # -----------------------------------------------------

        if best_match:

            candidates.append(best_match)

            position = best_match.end

        else:

            # No known ingredient starts at this position.
            #
            # Do not guess what the unknown text means.
            # Move forward and allow a later known ingredient
            # to be discovered.
            position += 1

    return candidates