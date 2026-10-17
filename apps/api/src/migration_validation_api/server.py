"""FastAPI transport and orchestration for the migration workbench."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from migration_data_engine import profile_dataset
from migration_audit import build_audit_package
from migration_input.input_contract import (
    CanonicalDataset,
    DatasetInputError,
    DatasetTooLarge,
    configuration_fingerprint,
    decode_base64_payload,
    read_dataset_bytes,
)
from migration_privacy.redaction import redact_result
from reconciliation_core.fuzzy import (
    DEFAULT_FUZZY_CANDIDATE_LIMIT,
    DEFAULT_FUZZY_THRESHOLD,
)
from reconciliation_core.normalization import available_profiles
from reconciliation_core.reconcile import generate_sql, reconcile


# Synthetic sample datasets ship inside the package (``sample_data`` is
# declared as package data), so "use sample data" works from a wheel or a
# non-editable install too. ``MIGRATION_WORKBENCH_FIXTURES`` still overrides.
SAMPLE_DATA_ROOT = Path(__file__).resolve().parent / "sample_data"
FIXTURE_ROOT = Path(os.environ.get("MIGRATION_WORKBENCH_FIXTURES") or SAMPLE_DATA_ROOT)
MAX_BODY_BYTES = 20 * 1024 * 1024


class FilePayload(BaseModel):
    """A native file encoded for the bounded in-memory API."""

    filename: str
    content_base64: str


class InspectPayload(FilePayload):
    """Input contract for schema inspection."""


class ReconcilePayload(BaseModel):
    """Request model that keeps the original CSV API backward compatible."""

    legacy_file_base64: str | None = None
    legacy_filename: str | None = None
    target_file_base64: str | None = None
    target_filename: str | None = None
    legacy_csv: str | None = None
    target_csv: str | None = None
    legacy_key: str = ""
    target_key: str = ""
    legacy_table: str = "legacy_table"
    target_table: str = "target_table"
    mapping: dict[str, str] | None = None
    redact_fields: list[str] = Field(default_factory=list)
    normalization_profile: str = "generic"
    review_statuses: dict[str, str] = Field(default_factory=dict)
    fuzzy_enabled: bool = True
    fuzzy_threshold: float = Field(default=DEFAULT_FUZZY_THRESHOLD, ge=0.0, le=1.0)
    fuzzy_candidate_limit: int = Field(
        default=DEFAULT_FUZZY_CANDIDATE_LIMIT, ge=1, le=5
    )


app = FastAPI(
    title="Migration Validation Workbench API",
    version="0.2.0",
    description="Local-first, deterministic migration reconciliation API.",
)


def _allowed_origins() -> list[str]:
    configured = os.getenv("MVW_ALLOWED_ORIGINS", "")
    if configured.strip():
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def request_size_guard(request: Request, call_next):
    """Reject oversized upload requests before FastAPI parses their JSON body."""

    if request.method == "POST" and request.url.path in {
        "/api/inspect",
        "/api/reconcile",
    }:
        content_length = request.headers.get("content-length")
        try:
            length = int(content_length or "0")
        except ValueError:
            return JSONResponse({"error": "Invalid Content-Length"}, status_code=400)
        if length <= 0 or length > MAX_BODY_BYTES:
            return JSONResponse(
                {"error": "Request body must be between 1 byte and 20 MB"},
                status_code=413,
            )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request, exc: RequestValidationError
):
    first_error = exc.errors()[0] if exc.errors() else {"msg": "Invalid request"}
    location = ".".join(
        str(part) for part in first_error.get("loc", []) if part != "body"
    )
    message = first_error.get("msg", "Invalid request")
    return JSONResponse(
        {"error": f"{location}: {message}" if location else message},
        status_code=422,
    )


def _input_error_status(exc: Exception) -> int:
    return 413 if isinstance(exc, DatasetTooLarge) else 400


@app.exception_handler(DatasetInputError)
async def dataset_input_error_handler(_request: Request, exc: DatasetInputError):
    return JSONResponse({"error": str(exc)}, status_code=_input_error_status(exc))


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": "migration-validation-workbench", "version": app.version}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "migration-validation-workbench",
        "version": app.version,
    }


@app.get("/api/normalization-profiles")
async def normalization_profiles() -> dict[str, Any]:
    return {"profiles": available_profiles()}


@app.get("/fixtures/{fixture_path:path}", include_in_schema=False)
async def fixture(fixture_path: str):
    """Serve only checked-in synthetic fixtures; never serve arbitrary paths."""

    relative = Path(unquote(fixture_path))
    resolved = (FIXTURE_ROOT / relative).resolve()
    fixture_root = FIXTURE_ROOT.resolve()
    if not resolved.is_relative_to(fixture_root) or not resolved.is_file():
        return JSONResponse({"error": "Not found"}, status_code=404)
    media_type = (
        "text/csv"
        if resolved.suffix.casefold() in {".csv", ".tsv"}
        else "application/octet-stream"
    )
    return FileResponse(resolved, media_type=media_type)


@app.post("/api/inspect")
async def inspect(payload: InspectPayload) -> dict[str, Any]:
    dataset = _dataset_from_file_payload(payload, "dataset")
    return {
        "input": dataset.metadata(),
        "engine": profile_dataset(dataset.fields, dataset.rows),
    }


@app.post("/api/reconcile", response_model=None)
async def reconcile_endpoint(
    payload: ReconcilePayload,
) -> dict[str, Any] | JSONResponse:
    try:
        legacy = _dataset_from_request(payload, "legacy")
        target = _dataset_from_request(payload, "target")
        if payload.mapping is not None and not isinstance(payload.mapping, dict):
            raise ValueError("mapping must be an object")

        result = reconcile(
            legacy.fields,
            legacy.rows,
            target.fields,
            target.rows,
            payload.legacy_key,
            payload.target_key,
            payload.mapping,
            payload.normalization_profile,
            payload.review_statuses,
            fuzzy_enabled=payload.fuzzy_enabled,
            fuzzy_threshold=payload.fuzzy_threshold,
            fuzzy_candidate_limit=payload.fuzzy_candidate_limit,
        )
        result["sql"] = generate_sql(
            payload.legacy_table,
            payload.target_table,
            payload.legacy_key,
            payload.target_key,
            result["applied_mapping"],
        )
        result["fields"] = {"legacy": legacy.fields, "target": target.fields}
        result["input"] = {"legacy": legacy.metadata(), "target": target.metadata()}
        result["engine"] = {
            "legacy": profile_dataset(legacy.fields, legacy.rows, payload.legacy_key),
            "target": profile_dataset(target.fields, target.rows, payload.target_key),
        }
        result["configuration_fingerprint"] = configuration_fingerprint(
            {
                "contract_version": legacy.metadata()["contract_version"],
                "legacy_key": payload.legacy_key,
                "target_key": payload.target_key,
                "mapping": result["applied_mapping"],
                "legacy_table": payload.legacy_table,
                "target_table": payload.target_table,
                "normalization_profile": result["normalization"]["name"],
                "fuzzy_matching": result["fuzzy_matching"],
            }
        )
        result["redacted_export"] = redact_result(
            result,
            legacy_key=payload.legacy_key,
            target_key=payload.target_key,
            fields=payload.redact_fields,
        )
        result["audit_package"] = build_audit_package(
            result,
            legacy_metadata=legacy.metadata(),
            target_metadata=target.metadata(),
            legacy_key=payload.legacy_key,
            target_key=payload.target_key,
            legacy_table=payload.legacy_table,
            target_table=payload.target_table,
            mapping=result["applied_mapping"],
            configuration_fingerprint=result["configuration_fingerprint"],
        )
        return result
    except (DatasetInputError, ValueError, TypeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=_input_error_status(exc))


def _dataset_from_file_payload(payload: BaseModel, prefix: str) -> CanonicalDataset:
    filename = getattr(payload, f"{prefix}_filename", None) or getattr(
        payload, "filename", ""
    )
    encoded = getattr(payload, f"{prefix}_file_base64", None) or getattr(
        payload, "content_base64", ""
    )
    return read_dataset_bytes(decode_base64_payload(encoded), str(filename))


def _dataset_from_request(payload: ReconcilePayload, side: str) -> CanonicalDataset:
    encoded = getattr(payload, f"{side}_file_base64")
    filename = getattr(payload, f"{side}_filename")
    if encoded is not None or filename is not None:
        return _dataset_from_file_payload(payload, side)
    csv_text = getattr(payload, f"{side}_csv")
    if not isinstance(csv_text, str):
        raise DatasetInputError(f"{side}_csv must be a string")
    return read_dataset_bytes(csv_text.encode("utf-8"), f"{side}.csv")


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the FastAPI app with Uvicorn for local development."""

    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")
