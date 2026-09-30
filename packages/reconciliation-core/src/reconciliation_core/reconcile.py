"""CSV reconciliation primitives.

The core intentionally has no external dependencies. It is deterministic so a
reviewer can explain every result and rerun the same comparison offline.
"""

from __future__ import annotations

import csv
import difflib
import io
import re
from collections import defaultdict
from typing import Any, Iterable, Mapping

from .fuzzy import (
    DEFAULT_FUZZY_CANDIDATE_LIMIT,
    DEFAULT_FUZZY_CANDIDATE_MINIMUM,
    DEFAULT_FUZZY_THRESHOLD,
    find_fuzzy_candidates,
)
from .normalization import (
    canonical_profile,
    normalize_value,
    profile_metadata,
)


STATUS_LABELS = {
    "match": "ตรงกัน",
    "value_mismatch": "ค่าไม่ตรง",
    "missing_target": "ไม่มีในระบบใหม่",
    "missing_legacy": "ไม่มีในระบบเก่า",
    "duplicate": "คีย์ซ้ำ",
    "invalid_key": "คีย์ไม่ถูกต้อง",
}

REVIEW_STATUS_LABELS = {
    "unreviewed": "ยังไม่ review",
    "approved": "อนุมัติ",
    "rejected": "ไม่อนุมัติ",
    "needs-review": "ต้องตรวจเพิ่ม",
}


def _string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_header(value: Any) -> str:
    """Normalize a column name for conservative matching."""

    return re.sub(r"[^a-z0-9]", "", _string(value).casefold())


def read_csv_text(text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse a UTF-8 CSV string and reject ambiguous headers."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("CSV must contain a header row and at least one character")

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV must contain a header row")

    raw_headers = list(reader.fieldnames)
    headers = [_string(header) for header in raw_headers]
    if any(not header for header in headers):
        raise ValueError("CSV headers cannot be blank")
    normalized_headers = [normalize_header(header) for header in headers]
    if len(set(normalized_headers)) != len(normalized_headers):
        raise ValueError("CSV headers must be unique")

    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({header: _string(row.get(raw_header)) for header, raw_header in zip(headers, raw_headers)})
    return headers, rows


def _token_set(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if token}


def suggest_mapping(source_fields: Iterable[str], target_fields: Iterable[str]) -> list[dict[str, Any]]:
    """Suggest one target field per source field with explainable confidence."""

    targets = list(target_fields)
    suggestions: list[dict[str, Any]] = []
    for source in source_fields:
        source_norm = normalize_header(source)
        best: tuple[float, str | None, str] = (0.0, None, "none")
        for target in targets:
            target_norm = normalize_header(target)
            if source_norm and source_norm == target_norm:
                candidate = (1.0, target, "exact normalized name")
            else:
                sequence = difflib.SequenceMatcher(None, source_norm, target_norm).ratio()
                source_tokens = _token_set(source)
                target_tokens = _token_set(target)
                overlap = (
                    len(source_tokens & target_tokens) / len(source_tokens | target_tokens)
                    if source_tokens and target_tokens
                    else 0.0
                )
                score = max(sequence, overlap)
                candidate = (score, target, "similar name")
            if candidate[0] > best[0]:
                best = candidate

        score, target, method = best
        suggestions.append(
            {
                "source": source,
                "target": target if score >= 0.35 else None,
                "confidence": round(score, 2),
                "method": method if target and score >= 0.35 else "no safe suggestion",
                "auto_selected": bool(target and score >= 0.78),
            }
        )
    return suggestions


def _index_by_key(
    rows: list[dict[str, str]],
    key_field: str,
    normalization_profile: str = "generic",
) -> dict[str, list[tuple[int, dict[str, str]]]]:
    index: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for row_number, row in enumerate(rows, start=1):
        key = normalize_value(
            row.get(key_field),
            profile=normalization_profile,
            field_name=key_field,
        )
        if key:
            index[key].append((row_number, row))
    return dict(index)


def _mismatch_fields(
    legacy_row: Mapping[str, str],
    target_row: Mapping[str, str],
    mapping: Mapping[str, str],
    normalization_profile: str,
) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []
    for legacy_field, target_field in mapping.items():
        legacy_value = _string(legacy_row.get(legacy_field))
        target_value = _string(target_row.get(target_field))
        if normalize_value(
            legacy_value,
            profile=normalization_profile,
            field_name=legacy_field,
        ) != normalize_value(
            target_value,
            profile=normalization_profile,
            field_name=target_field,
        ):
            mismatches.append(
                {
                    "legacy_field": legacy_field,
                    "target_field": target_field,
                    "legacy_value": legacy_value,
                    "target_value": target_value,
                }
            )
    return mismatches


def _record(
    *,
    status: str,
    key: str,
    legacy_row: Mapping[str, str] | None = None,
    target_row: Mapping[str, str] | None = None,
    mismatches: list[dict[str, str]] | None = None,
    reason: str,
    legacy_row_number: int | None = None,
    target_row_number: int | None = None,
    match_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_id = f"{status}:legacy-{legacy_row_number or 0}:target-{target_row_number or 0}"
    return {
        "evidence_id": evidence_id,
        "status": status,
        "status_label": STATUS_LABELS[status],
        "key": key,
        "reason": reason,
        "legacy_row": legacy_row_number,
        "target_row": target_row_number,
        "legacy": dict(legacy_row) if legacy_row is not None else None,
        "target": dict(target_row) if target_row is not None else None,
        "mismatches": mismatches or [],
        "match_candidates": match_candidates or [],
        "review_status": "unreviewed",
    }


def reconcile(
    legacy_fields: list[str],
    legacy_rows: list[dict[str, str]],
    target_fields: list[str],
    target_rows: list[dict[str, str]],
    legacy_key: str,
    target_key: str,
    mapping: Mapping[str, str] | None = None,
    normalization_profile: str = "generic",
    review_statuses: Mapping[str, str] | None = None,
    fuzzy_enabled: bool = True,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    fuzzy_candidate_limit: int = DEFAULT_FUZZY_CANDIDATE_LIMIT,
) -> dict[str, Any]:
    """Compare two datasets and return summary plus reviewable evidence."""

    if legacy_key not in legacy_fields or target_key not in target_fields:
        raise ValueError("Selected key must exist in its dataset")
    selected_profile = canonical_profile(normalization_profile)
    if not 0.0 <= fuzzy_threshold <= 1.0:
        raise ValueError("fuzzy_threshold must be between 0 and 1")
    if fuzzy_candidate_limit < 1 or fuzzy_candidate_limit > 5:
        raise ValueError("fuzzy_candidate_limit must be between 1 and 5")

    suggestions = suggest_mapping(legacy_fields, target_fields)
    if mapping is None:
        resolved_mapping = {
            item["source"]: item["target"]
            for item in suggestions
            if item["target"] and item["auto_selected"]
        }
    else:
        resolved_mapping = {
            _string(source): _string(target)
            for source, target in mapping.items()
            if _string(source) in legacy_fields and _string(target) in target_fields
        }
    resolved_mapping[legacy_key] = target_key
    comparison_mapping = {
        source: target for source, target in resolved_mapping.items() if source != legacy_key
    }

    legacy_index = _index_by_key(legacy_rows, legacy_key, selected_profile)
    target_index = _index_by_key(target_rows, target_key, selected_profile)
    evidence: list[dict[str, Any]] = []

    for row_number, legacy_row in enumerate(legacy_rows, start=1):
        raw_key = _string(legacy_row.get(legacy_key))
        comparison_key = normalize_value(
            raw_key,
            profile=selected_profile,
            field_name=legacy_key,
        )
        if not comparison_key:
            evidence.append(
                _record(
                    status="invalid_key",
                    key="(blank)",
                    legacy_row=legacy_row,
                    reason=f"Legacy key '{legacy_key}' is blank",
                    legacy_row_number=row_number,
                )
            )
            continue

        legacy_matches = legacy_index.get(comparison_key, [])
        target_matches = target_index.get(comparison_key, [])
        if len(legacy_matches) > 1 or len(target_matches) > 1:
            evidence.append(
                _record(
                    status="duplicate",
                    key=raw_key,
                    legacy_row=legacy_row,
                    target_row=target_matches[0][1] if target_matches else None,
                    reason="The reconciliation key appears more than once on one or both sides",
                    legacy_row_number=row_number,
                    target_row_number=target_matches[0][0] if target_matches else None,
                )
            )
            continue

        if not target_matches:
            candidates = (
                find_fuzzy_candidates(
                    legacy_row,
                    target_rows,
                    comparison_mapping,
                    selected_profile,
                    candidate_key=target_key,
                    threshold=fuzzy_threshold,
                    limit=fuzzy_candidate_limit,
                )
                if fuzzy_enabled
                else []
            )
            evidence.append(
                _record(
                    status="missing_target",
                    key=raw_key,
                    legacy_row=legacy_row,
                    reason="No target record exists for this key",
                    legacy_row_number=row_number,
                    match_candidates=candidates,
                )
            )
            continue

        target_row_number, target_row = target_matches[0]
        mismatches = _mismatch_fields(
            legacy_row,
            target_row,
            comparison_mapping,
            selected_profile,
        )
        evidence.append(
            _record(
                status="value_mismatch" if mismatches else "match",
                key=raw_key,
                legacy_row=legacy_row,
                target_row=target_row,
                mismatches=mismatches,
                reason=(
                    f"{len(mismatches)} mapped field(s) differ"
                    if mismatches
                    else "All selected mapped fields match"
                ),
                legacy_row_number=row_number,
                target_row_number=target_row_number,
            )
        )

    legacy_keys = set(legacy_index)
    for row_number, target_row in enumerate(target_rows, start=1):
        raw_key = _string(target_row.get(target_key))
        comparison_key = normalize_value(
            raw_key,
            profile=selected_profile,
            field_name=target_key,
        )
        if comparison_key and comparison_key not in legacy_keys:
            candidates = (
                find_fuzzy_candidates(
                    target_row,
                    legacy_rows,
                    {target_field: legacy_field for legacy_field, target_field in comparison_mapping.items()},
                    selected_profile,
                    candidate_key=legacy_key,
                    threshold=fuzzy_threshold,
                    limit=fuzzy_candidate_limit,
                )
                if fuzzy_enabled
                else []
            )
            evidence.append(
                _record(
                    status="missing_legacy",
                    key=raw_key,
                    target_row=target_row,
                    reason="Target record has no corresponding legacy record",
                    target_row_number=row_number,
                    match_candidates=candidates,
                )
            )

    counts = {status: 0 for status in STATUS_LABELS}
    for item in evidence:
        counts[item["status"]] += 1
    known_evidence_ids = {item["evidence_id"] for item in evidence}
    requested_review_ids = set(review_statuses or {})
    unknown_review_ids = requested_review_ids - known_evidence_ids
    if unknown_review_ids:
        raise ValueError("review_statuses contains an unknown evidence_id")
    for item in evidence:
        review_status = (review_statuses or {}).get(item["evidence_id"], "unreviewed")
        if review_status not in REVIEW_STATUS_LABELS:
            raise ValueError(f"Unknown review status: {review_status}")
        item["review_status"] = review_status
    review_summary = {
        status: sum(1 for item in evidence if item["review_status"] == status)
        for status in REVIEW_STATUS_LABELS
    }
    checked = len(legacy_rows)
    matched = counts["match"]
    exceptions = checked - matched + counts["missing_legacy"]
    summary = {
        "records_checked": checked,
        "legacy_records": len(legacy_rows),
        "target_records": len(target_rows),
        "matched": matched,
        "exceptions": exceptions,
        "match_rate": round((matched / checked * 100) if checked else 0.0, 1),
        "counts": counts,
    }
    return {
        "summary": summary,
        "mapping_suggestions": suggestions,
        "applied_mapping": resolved_mapping,
        "normalization": profile_metadata(selected_profile),
        "fuzzy_matching": {
            "enabled": fuzzy_enabled,
            "candidate_minimum": DEFAULT_FUZZY_CANDIDATE_MINIMUM,
            "review_threshold": fuzzy_threshold,
            "candidate_limit": fuzzy_candidate_limit,
            "auto_approval": False,
        },
        "review_summary": review_summary,
        "evidence": evidence,
    }


def _quote_identifier(identifier: str) -> str:
    """Quote a simple SQL identifier or schema-qualified identifier."""

    parts = identifier.split(".")
    if not parts or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) for part in parts):
        raise ValueError("SQL identifiers may contain letters, numbers, underscores and dots only")
    return ".".join(f'"{part}"' for part in parts)


_MAX_COLUMN_IDENTIFIER_CHARS = 128


def _quote_column(identifier: str) -> str:
    """Quote a CSV-derived column name as one delimited SQL identifier.

    Real headers contain spaces, Thai text, dots or quotes ("Customer Name"),
    so they cannot use the strict table-name rule. Standard SQL delimited
    identifiers are safe for any text once embedded double quotes are doubled;
    control characters are rejected so the generated query stays readable.
    """

    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("SQL column identifiers cannot be blank")
    if len(identifier) > _MAX_COLUMN_IDENTIFIER_CHARS:
        raise ValueError(f"SQL column identifiers are limited to {_MAX_COLUMN_IDENTIFIER_CHARS} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in identifier):
        raise ValueError("SQL column identifiers cannot contain control characters")
    return '"' + identifier.replace('"', '""') + '"'


def generate_sql(
    legacy_table: str,
    target_table: str,
    legacy_key: str,
    target_key: str,
    mapping: Mapping[str, str],
) -> str:
    """Generate a read-only SQL verification query for a mapped pair."""

    legacy_table_sql = _quote_identifier(legacy_table)
    target_table_sql = _quote_identifier(target_table)
    legacy_key_sql = _quote_column(legacy_key)
    target_key_sql = _quote_column(target_key)
    comparisons = []
    for legacy_field, target_field in mapping.items():
        if legacy_field == legacy_key:
            continue
        comparisons.append(
            f"    OR COALESCE(CAST(l.{_quote_column(legacy_field)} AS TEXT), '') "
            f"<> COALESCE(CAST(t.{_quote_column(target_field)} AS TEXT), '')"
        )
    mismatch_clause = "\n".join(comparisons) or "    OR 1 = 0"
    return (
        "-- Read-only migration verification query\n"
        f"SELECT l.{legacy_key_sql} AS legacy_key, t.{target_key_sql} AS target_key\n"
        f"FROM {legacy_table_sql} AS l\n"
        f"FULL OUTER JOIN {target_table_sql} AS t\n"
        f"  ON CAST(l.{legacy_key_sql} AS TEXT) = CAST(t.{target_key_sql} AS TEXT)\n"
        "WHERE\n"
        f"    l.{legacy_key_sql} IS NULL\n"
        f"    OR t.{target_key_sql} IS NULL\n"
        f"{mismatch_clause};\n"
    )
