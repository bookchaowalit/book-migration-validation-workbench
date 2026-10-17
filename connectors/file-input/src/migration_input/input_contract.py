"""Canonical input contract for the local migration workbench.

The workbench accepts native file bytes but normalizes every supported format to
the same fields/rows representation before reconciliation. Raw bytes are never
written to disk by this module.
"""

from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree

from reconciliation_core.reconcile import normalize_header, read_csv_text

INPUT_CONTRACT_VERSION = "mvw.input.v1"
_CELL_REFERENCE_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*$")
# Excel's own column limit (XFD). A crafted reference such as "ZZZZZZZ1"
# would otherwise make the row matrix allocate billions of empty cells.
_XLSX_MAX_COLUMNS = 16_384
# Upper bound on the decompressed size of any XLSX part we read, so a small
# upload cannot expand into gigabytes in memory (zip bomb).
_XLSX_MAX_PART_BYTES = 100 * 1024 * 1024
# Shape limits for one dataset. Reconciliation keeps both sides in memory and
# fuzzy matching is super-linear, so oversized inputs are refused up front.
MAX_DATASET_ROWS = 200_000
MAX_DATASET_COLUMNS = 500


class DatasetInputError(ValueError):
    """Raised when an input cannot be safely normalized."""


class DatasetTooLarge(DatasetInputError):
    """Raised when a dataset exceeds the row or column limit (HTTP 413)."""


def _check_rows(count: int) -> None:
    if count > MAX_DATASET_ROWS:
        raise DatasetTooLarge(
            f"Dataset exceeds the {MAX_DATASET_ROWS:,} data-row limit"
        )


class ParquetUnavailable(DatasetInputError):
    """Raised when Parquet input is requested without PyArrow."""


@dataclass
class CanonicalDataset:
    """Normalized dataset plus non-sensitive source metadata."""

    filename: str
    source_format: str
    fields: list[str]
    rows: list[dict[str, str]]
    content_sha256: str
    byte_size: int

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def metadata(self) -> dict[str, Any]:
        return {
            "contract_version": INPUT_CONTRACT_VERSION,
            "filename": self.filename,
            "format": self.source_format,
            "fields": self.fields,
            "row_count": self.row_count,
            "byte_size": self.byte_size,
            "sha256": self.content_sha256,
        }


def content_fingerprint(payload: bytes) -> str:
    """Return a stable fingerprint of exact input bytes."""

    return hashlib.sha256(payload).hexdigest()


def configuration_fingerprint(configuration: Mapping[str, Any]) -> str:
    """Return a stable fingerprint without storing the configuration payload."""

    canonical = json.dumps(
        configuration,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return content_fingerprint(canonical)


def decode_base64_payload(value: Any) -> bytes:
    """Decode a request payload without echoing encoded content in errors."""

    if not isinstance(value, str) or not value:
        raise DatasetInputError("content_base64 must be a non-empty string")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise DatasetInputError("content_base64 is not valid base64") from exc


def _safe_filename(filename: Any) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise DatasetInputError("filename must be a non-empty string")
    if "\x00" in filename:
        raise DatasetInputError("filename contains an invalid character")
    safe = PurePosixPath(filename.replace("\\", "/")).name.strip()
    if not safe or safe in {".", ".."}:
        raise DatasetInputError("filename is invalid")
    return safe


def _format_from_filename(filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.casefold()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix == ".xlsx":
        return "xlsx"
    if suffix == ".parquet":
        return "parquet"
    raise DatasetInputError("Supported input formats are CSV, XLSX and Parquet")


def _validate_headers(raw_headers: Iterable[Any]) -> list[str]:
    headers = ["" if value is None else str(value).strip() for value in raw_headers]
    if len(headers) > MAX_DATASET_COLUMNS:
        raise DatasetTooLarge(f"Dataset exceeds the {MAX_DATASET_COLUMNS} column limit")
    if not headers or any(not header for header in headers):
        raise DatasetInputError("Dataset headers cannot be blank")
    normalized_headers = [normalize_header(header) for header in headers]
    if len(set(normalized_headers)) != len(normalized_headers):
        raise DatasetInputError("Dataset headers must be unique")
    return headers


def _rows_from_matrix(
    matrix: list[list[Any]],
) -> tuple[list[str], list[dict[str, str]]]:
    if not matrix:
        raise DatasetInputError("Dataset must contain a header row")
    fields = _validate_headers(matrix[0])
    rows: list[dict[str, str]] = []
    for values in matrix[1:]:
        padded = list(values[: len(fields)]) + [""] * max(0, len(fields) - len(values))
        normalized = ["" if value is None else str(value).strip() for value in padded]
        if not any(normalized):
            continue
        rows.append(dict(zip(fields, normalized)))
    return fields, rows


def _read_csv(payload: bytes, filename: str) -> tuple[list[str], list[dict[str, str]]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DatasetInputError("CSV must be UTF-8 encoded") from exc
    if PurePosixPath(filename).suffix.casefold() == ".tsv":
        reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t")
        return _rows_from_matrix([list(row) for row in reader])
    try:
        return read_csv_text(text)
    except ValueError as exc:
        raise DatasetInputError(str(exc)) from exc


def _column_index(cell_reference: str) -> int:
    if not _CELL_REFERENCE_RE.fullmatch(cell_reference):
        raise DatasetInputError("XLSX contains an invalid cell reference")
    letters = re.match(r"^[A-Z]+", cell_reference)
    assert letters is not None
    value = 0
    for char in letters.group(0):
        value = value * 26 + ord(char) - ord("A") + 1
    if value > _XLSX_MAX_COLUMNS:
        raise DatasetInputError("XLSX cell reference exceeds the 16,384 column limit")
    return value - 1


def _xml_text(element: ElementTree.Element) -> str:
    return "".join(element.itertext()).strip()


def _read_xlsx(payload: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except (zipfile.BadZipFile, OSError) as exc:
        raise DatasetInputError("XLSX archive is invalid") from exc

    namespaces = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    try:
        with archive:
            names = set(archive.namelist())
            if "xl/worksheets/sheet1.xml" not in names:
                raise DatasetInputError("XLSX must contain the first worksheet")
            for part in ("xl/worksheets/sheet1.xml", "xl/sharedStrings.xml"):
                if (
                    part in names
                    and archive.getinfo(part).file_size > _XLSX_MAX_PART_BYTES
                ):
                    raise DatasetInputError(
                        "XLSX content exceeds the 100 MB decompressed limit"
                    )
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in names:
                shared_root = ElementTree.fromstring(
                    archive.read("xl/sharedStrings.xml")
                )
                shared_strings = [
                    _xml_text(item)
                    for item in shared_root.findall("main:si", namespaces)
                ]

            root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            matrix: list[list[str]] = []
            for row_element in root.findall(".//main:sheetData/main:row", namespaces):
                cells: dict[int, str] = {}
                for cell in row_element.findall("main:c", namespaces):
                    column = _column_index(cell.attrib.get("r", ""))
                    # Bound every cell, including empty/data cells, before
                    # decoding its value or expanding the sparse row.
                    if column >= MAX_DATASET_COLUMNS:
                        raise DatasetTooLarge(
                            f"Dataset exceeds the {MAX_DATASET_COLUMNS} column limit"
                        )
                    cell_type = cell.attrib.get("t", "")
                    inline = cell.find("main:is", namespaces)
                    if cell_type == "inlineStr":
                        value = _xml_text(inline) if inline is not None else ""
                    else:
                        value_element = cell.find("main:v", namespaces)
                        value = (
                            value_element.text.strip()
                            if value_element is not None and value_element.text
                            else ""
                        )
                        if cell_type == "s" and value:
                            try:
                                value = shared_strings[int(value)]
                            except (IndexError, ValueError) as exc:
                                raise DatasetInputError(
                                    "XLSX shared string reference is invalid"
                                ) from exc
                        elif cell_type == "b":
                            value = "TRUE" if value == "1" else "FALSE"
                    cells[column] = value
                if cells:
                    width = max(cells) + 1
                    matrix.append([cells.get(index, "") for index in range(width)])
                    # Header row + data rows; fail before materialising more.
                    _check_rows(len(matrix) - 1)
    except DatasetInputError:
        raise
    except (ElementTree.ParseError, KeyError, OSError, zipfile.BadZipFile) as exc:
        # BadZipFile covers CRC mismatches, e.g. a part whose header lies about
        # its decompressed size.
        raise DatasetInputError("XLSX worksheet could not be read") from exc
    return _rows_from_matrix(matrix)


def _read_parquet(payload: bytes) -> tuple[list[str], list[dict[str, str]]]:
    try:
        from pyarrow import parquet  # type: ignore
    except ImportError as exc:
        raise ParquetUnavailable(
            "Parquet input requires PyArrow; install the repository data-lake runtime or use CSV/XLSX"
        ) from exc
    try:
        table = parquet.read_table(io.BytesIO(payload))
        fields = _validate_headers(table.column_names)
        rows = [
            {
                field: "" if row.get(field) is None else str(row.get(field)).strip()
                for field in fields
            }
            for row in table.to_pylist()
        ]
        return fields, rows
    except DatasetInputError:
        raise
    except Exception as exc:  # pyarrow has multiple format-specific exception types
        raise DatasetInputError("Parquet file could not be read") from exc


def read_dataset_bytes(payload: bytes, filename: str) -> CanonicalDataset:
    """Normalize supported file bytes into the canonical input contract."""

    if not isinstance(payload, bytes) or not payload:
        raise DatasetInputError("Input file must contain at least one byte")
    safe_filename = _safe_filename(filename)
    source_format = _format_from_filename(safe_filename)
    if source_format == "csv":
        fields, rows = _read_csv(payload, safe_filename)
    elif source_format == "xlsx":
        fields, rows = _read_xlsx(payload)
    else:
        fields, rows = _read_parquet(payload)
    if len(fields) > MAX_DATASET_COLUMNS:
        raise DatasetTooLarge(f"Dataset exceeds the {MAX_DATASET_COLUMNS} column limit")
    _check_rows(len(rows))
    return CanonicalDataset(
        filename=safe_filename,
        source_format=source_format,
        fields=fields,
        rows=rows,
        content_sha256=content_fingerprint(payload),
        byte_size=len(payload),
    )
