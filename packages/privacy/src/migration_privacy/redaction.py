"""Field-profile redaction for safe demo and pilot exports."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


DEFAULT_SENSITIVE_TOKENS = (
    "address",
    "email",
    "name",
    "passport",
    "phone",
    "mobile",
    "tax",
)
REDACTED = "[REDACTED]"


def default_redact_fields(fields: Iterable[str]) -> set[str]:
    """Select conservative PII-like fields without treating every ID as PII."""

    return {
        field
        for field in fields
        if any(token in field.casefold().replace("-", "_") for token in DEFAULT_SENSITIVE_TOKENS)
    }


def redact_result(
    result: Mapping[str, Any],
    *,
    legacy_key: str,
    target_key: str,
    fields: Iterable[str] = (),
) -> dict[str, Any]:
    """Return a deep-copied result with selected evidence values redacted."""

    redacted = deepcopy(dict(result))
    explicit_fields = {str(field) for field in fields if str(field).strip()}
    all_fields = set(explicit_fields)
    for item in redacted.get("evidence", []):
        for side in ("legacy", "target"):
            row = item.get(side)
            if isinstance(row, dict):
                all_fields.update(row)
    selected_fields = explicit_fields or default_redact_fields(all_fields)

    for item in redacted.get("evidence", []):
        for side in ("legacy", "target"):
            row = item.get(side)
            if isinstance(row, dict):
                for field in selected_fields:
                    if field in row:
                        row[field] = REDACTED
        for diff in item.get("mismatches", []):
            if diff.get("legacy_field") in selected_fields:
                diff["legacy_value"] = REDACTED
            if diff.get("target_field") in selected_fields:
                diff["target_value"] = REDACTED
        for candidate in item.get("match_candidates", []):
            if isinstance(candidate, dict):
                candidate_fields = {
                    field
                    for field in (candidate.get("candidate_field"), candidate.get("target_field"))
                    if field
                }
                for field_score in candidate.get("field_scores", []):
                    if isinstance(field_score, dict):
                        candidate_fields.update(
                            field
                            for field in (
                                field_score.get("source_field"),
                                field_score.get("candidate_field"),
                                field_score.get("legacy_field"),
                                field_score.get("target_field"),
                            )
                            if field
                        )
                if (
                    candidate_fields & selected_fields
                    or legacy_key in selected_fields
                    or target_key in selected_fields
                ):
                    candidate["target_key"] = REDACTED
                    candidate["candidate_key"] = REDACTED
        if legacy_key in selected_fields or target_key in selected_fields:
            item["key"] = REDACTED

    redacted["redaction"] = {
        "mode": "field_profile",
        "fields": sorted(selected_fields),
        "raw_values_included": False,
    }
    return redacted
