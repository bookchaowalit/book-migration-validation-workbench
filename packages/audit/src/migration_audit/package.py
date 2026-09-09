"""Build a deterministic, privacy-safe audit artifact for one run."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


AUDIT_SCHEMA_VERSION = "mvw.audit.v1"
RULE_VERSION = "reconciliation-core@0.2.0"


def _fingerprint(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _metadata_snapshot(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Keep source metadata useful for reruns without copying dataset values."""

    allowed = (
        "contract_version",
        "filename",
        "format",
        "fields",
        "row_count",
        "byte_size",
        "sha256",
    )
    return {key: metadata[key] for key in allowed if key in metadata}


def _field_scores(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for field_score in candidate.get("field_scores", []):
        if not isinstance(field_score, Mapping):
            continue
        item = {
            key: field_score[key]
            for key in (
                "source_field",
                "candidate_field",
                "legacy_field",
                "target_field",
                "score",
            )
            if key in field_score
        }
        scores.append(item)
    return scores


def _evidence_reference(item: Mapping[str, Any]) -> dict[str, Any]:
    """Return evidence references only; no row, key, or field values are copied."""

    reference: dict[str, Any] = {
        "evidence_id": item.get("evidence_id"),
        "status": item.get("status"),
        "review_status": item.get("review_status", "unreviewed"),
        "reason": item.get("reason"),
        "legacy_row": item.get("legacy_row"),
        "target_row": item.get("target_row"),
        "mismatch_fields": [
            {
                key: mismatch[key]
                for key in ("legacy_field", "target_field")
                if key in mismatch
            }
            for mismatch in item.get("mismatches", [])
            if isinstance(mismatch, Mapping)
        ],
        "match_candidates": [],
    }
    for candidate in item.get("match_candidates", []):
        if not isinstance(candidate, Mapping):
            continue
        reference["match_candidates"].append(
            {
                key: candidate[key]
                for key in ("row_number", "score", "threshold", "auto_approved", "reason")
                if key in candidate
            }
            | {"field_scores": _field_scores(candidate)}
        )
    return reference


def build_audit_package(
    result: Mapping[str, Any],
    *,
    legacy_metadata: Mapping[str, Any],
    target_metadata: Mapping[str, Any],
    legacy_key: str,
    target_key: str,
    legacy_table: str,
    target_table: str,
    mapping: Mapping[str, str],
    configuration_fingerprint: str,
) -> dict[str, Any]:
    """Create a stable audit package for export and later review.

    The package intentionally contains row references and field names, but not
    source rows, keys, mismatch values, or fuzzy candidate keys.
    """

    package: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "rule_version": RULE_VERSION,
        "inputs": {
            "legacy": _metadata_snapshot(legacy_metadata),
            "target": _metadata_snapshot(target_metadata),
        },
        "configuration": {
            "legacy_key": legacy_key,
            "target_key": target_key,
            "legacy_table": legacy_table,
            "target_table": target_table,
            "mapping": dict(sorted(mapping.items())),
            "normalization": result.get("normalization", {}),
            "fuzzy_matching": result.get("fuzzy_matching", {}),
        },
        "fingerprints": {
            "legacy_input_sha256": legacy_metadata.get("sha256"),
            "target_input_sha256": target_metadata.get("sha256"),
            "configuration_sha256": configuration_fingerprint,
        },
        "summary": result.get("summary", {}),
        "review_summary": result.get("review_summary", {}),
        "evidence": [_evidence_reference(item) for item in result.get("evidence", [])],
        "privacy": {
            "raw_values_included": False,
            "evidence_mode": "row_and_field_references",
            "note": "Source rows, keys, mismatch values, and candidate keys are omitted.",
        },
    }
    package["fingerprints"]["audit_package_sha256"] = _fingerprint(package)
    return package
