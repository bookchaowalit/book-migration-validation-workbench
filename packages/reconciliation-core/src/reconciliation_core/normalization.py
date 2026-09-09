"""Conservative, field-aware normalization profiles for reconciliation."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any


class NormalizationProfileError(ValueError):
    """Raised when a requested normalization profile is not registered."""


PROFILE_ALIASES = {
    "default": "generic",
    "thai": "thai_customer",
    "customer_th": "thai_customer",
}

PROFILE_DEFINITIONS = {
    "generic": {
        "label": "Generic",
        "description": "Unicode normalization, case folding and whitespace collapse",
        "field_rules": ["text"],
    },
    "thai_customer": {
        "label": "Thai customer",
        "description": "Generic text plus conservative Thai customer field rules",
        "field_rules": ["name", "phone", "tax_id", "date", "address"],
    },
}


def canonical_profile(profile: str | None) -> str:
    """Resolve a profile name and fail closed for unknown profiles."""

    candidate = str(profile or "generic").strip().casefold()
    candidate = PROFILE_ALIASES.get(candidate, candidate)
    if candidate not in PROFILE_DEFINITIONS:
        supported = ", ".join(PROFILE_DEFINITIONS)
        raise NormalizationProfileError(
            f"Unknown normalization profile '{profile}'. Supported profiles: {supported}"
        )
    return candidate


def available_profiles() -> list[dict[str, Any]]:
    """Return a JSON-safe registry for the UI and API documentation."""

    return [
        {"name": name, **definition, "raw_evidence_preserved": True}
        for name, definition in PROFILE_DEFINITIONS.items()
    ]


def profile_metadata(profile: str | None) -> dict[str, Any]:
    """Return the selected profile contract without exposing input values."""

    name = canonical_profile(profile)
    return {"name": name, **PROFILE_DEFINITIONS[name], "raw_evidence_preserved": True}


def _text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", "" if value is None else str(value))
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _field_kind(field_name: str | None) -> str:
    normalized = _text(field_name).replace("_", " ")
    if any(token in normalized for token in ("phone", "mobile", "tel", "โทร", "เบอร์")):
        return "phone"
    if any(token in normalized for token in ("tax", "vat", "ภาษี")):
        return "tax_id"
    if any(token in normalized for token in ("date", "วันที่", "วันเวลา")):
        return "date"
    if any(token in normalized for token in ("address", "ที่อยู่")):
        return "address"
    if any(token in normalized for token in ("name", "ชื่อ")):
        return "name"
    return "text"


def _normalize_name(value: str) -> str:
    # Remove only an honorific followed by whitespace; avoid changing names
    # such as "นายก" where the prefix may be part of the actual value.
    return re.sub(
        r"^(?:นาย|นางสาว|นาง|เด็กชาย|เด็กหญิง|mr\.?|mrs\.?|ms\.?|miss)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value)
    # Convert the common Thai international form +66 8x xxx xxxx to 0 8x...
    if digits.startswith("66") and len(digits) == 11:
        return "0" + digits[2:]
    return digits


def _normalize_tax_id(value: str) -> str:
    return re.sub(r"\D+", "", value)


def _normalize_date(value: str) -> str:
    candidate = value.replace(" ", "")
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
    )
    for date_format in formats:
        try:
            parsed = datetime.strptime(candidate, date_format)
        except ValueError:
            continue
        year = parsed.year - 543 if parsed.year >= 2400 else parsed.year
        return f"{year:04d}-{parsed.month:02d}-{parsed.day:02d}"
    return value


def _normalize_address(value: str) -> str:
    # Keep house-number slashes and words intact; only normalize separators
    # that commonly differ between spreadsheet exports.
    return re.sub(r"\s+", " ", re.sub(r"[,;，；\r\n\t]+", " ", value)).strip()


def normalize_value(
    value: Any,
    *,
    profile: str | None = "generic",
    field_name: str | None = None,
) -> str:
    """Normalize a comparison value while leaving the original evidence untouched."""

    selected = canonical_profile(profile)
    normalized = _text(value)
    if selected == "generic":
        return normalized

    kind = _field_kind(field_name)
    if kind == "name":
        return _normalize_name(normalized)
    if kind == "phone":
        return _normalize_phone(normalized)
    if kind == "tax_id":
        return _normalize_tax_id(normalized)
    if kind == "date":
        return _normalize_date(normalized)
    if kind == "address":
        return _normalize_address(normalized)
    return normalized
