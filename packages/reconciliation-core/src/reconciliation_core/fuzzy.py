"""Bounded fuzzy candidate suggestions for human review."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping

from .normalization import normalize_value


DEFAULT_FUZZY_THRESHOLD = 0.90
DEFAULT_FUZZY_CANDIDATE_LIMIT = 3
DEFAULT_FUZZY_CANDIDATE_MINIMUM = 0.55
MAX_FUZZY_CANDIDATE_ROWS = 2_000


def fuzzy_score(left: str, right: str) -> float:
    """Return a deterministic similarity score in the inclusive range [0, 1]."""

    if not left or not right:
        return 0.0
    return round(SequenceMatcher(None, left, right).ratio(), 2)


def find_fuzzy_candidates(
    source_row: Mapping[str, Any],
    candidate_rows: Iterable[Mapping[str, Any]],
    mapping: Mapping[str, str],
    normalization_profile: str,
    *,
    candidate_key: str,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    minimum_score: float = DEFAULT_FUZZY_CANDIDATE_MINIMUM,
    limit: int = DEFAULT_FUZZY_CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
    """Return bounded, field-aware candidates without approving any row."""

    rows = list(candidate_rows)
    if not mapping or len(rows) > MAX_FUZZY_CANDIDATE_ROWS or limit <= 0:
        return []

    candidates: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        field_scores: list[dict[str, Any]] = []
        for source_field, target_field in mapping.items():
            source_value = normalize_value(
                source_row.get(source_field),
                profile=normalization_profile,
                field_name=source_field,
            )
            target_value = normalize_value(
                row.get(target_field),
                profile=normalization_profile,
                field_name=target_field,
            )
            if not source_value or not target_value:
                continue
            field_scores.append(
                {
                    "legacy_field": source_field,
                    "target_field": target_field,
                    "source_field": source_field,
                    "candidate_field": target_field,
                    "score": fuzzy_score(source_value, target_value),
                }
            )
        if not field_scores:
            continue

        score = round(sum(item["score"] for item in field_scores) / len(field_scores), 2)
        if score < minimum_score:
            continue
        raw_candidate_key = "" if row.get(candidate_key) is None else str(row.get(candidate_key)).strip()
        candidates.append(
            {
                # target_key is kept for the V1 response contract. candidate_key
                # makes the same shape usable for target-only evidence later.
                "target_key": raw_candidate_key,
                "candidate_key": raw_candidate_key,
                "score": score,
                "threshold": threshold,
                "auto_approved": False,
                "reason": (
                    "High-confidence candidate; human review is still required because the key differs"
                    if score >= threshold
                    else "Below conservative review threshold; candidate is not auto-approved"
                ),
                "field_scores": field_scores,
                "row_number": row_number,
            }
        )

    candidates.sort(key=lambda item: (-item["score"], item["row_number"], item["candidate_key"]))
    return candidates[:limit]
