"""Small data-engine adapter used by the API boundary.

The reconciliation result remains deterministic Python business logic. This
module owns tabular profiling so the runtime can move from inline request rows
to DuckDB/Arrow relations without changing the API contract.
"""

from __future__ import annotations

from typing import Any

try:
    import duckdb  # type: ignore
except ImportError:  # pragma: no cover - exercised in the dependency-free fallback
    duckdb = None  # type: ignore[assignment]


MAX_INLINE_ROWS = 5_000


def _python_profile(
    fields: list[str], rows: list[dict[str, str]], key_field: str | None, backend: str
) -> dict[str, Any]:
    key_values = [
        str(row.get(key_field, "")).strip()
        for row in rows
        if key_field and str(row.get(key_field, "")).strip()
    ]
    distinct_keys = len(set(key_values))
    return {
        "backend": backend,
        "row_count": len(rows),
        "field_count": len(fields),
        "blank_counts": {
            field: sum(1 for row in rows if not str(row.get(field, "")).strip())
            for field in fields
        },
        "key_field": key_field,
        "distinct_keys": distinct_keys,
        "duplicate_key_rows": max(0, len(key_values) - distinct_keys),
    }


def _duckdb_profile(
    fields: list[str], rows: list[dict[str, str]], key_field: str | None
) -> dict[str, Any]:
    if not rows:
        return _python_profile(fields, rows, key_field, "duckdb")

    connection = duckdb.connect(":memory:")  # type: ignore[union-attr]
    try:
        placeholders = ", ".join(f"({', '.join('?' for _ in fields)})" for _ in rows)
        values = [str(row.get(field, "")) for row in rows for field in fields]
        columns = ", ".join(f'"col{index}"' for index in range(len(fields)))
        select_parts = ["COUNT(*) AS row_count"]
        select_parts.extend(
            f"SUM(CASE WHEN NULLIF(CAST(\"col{index}\" AS VARCHAR), '') IS NULL THEN 1 ELSE 0 END) AS blank_{index}"
            for index in range(len(fields))
        )
        key_index = fields.index(key_field) if key_field in fields else None
        if key_index is not None:
            select_parts.append(
                f"COUNT(DISTINCT NULLIF(CAST(\"col{key_index}\" AS VARCHAR), '')) AS distinct_keys"
            )
        query = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM (VALUES {placeholders}) AS dataset({columns})"
        )
        result = connection.execute(query, values).fetchone()
        assert result is not None
        row_count = int(result[0])
        blank_counts = {
            field: int(result[index + 1] or 0) for index, field in enumerate(fields)
        }
        distinct_keys = (
            int(result[len(fields) + 1] or 0) if key_index is not None else 0
        )
        return {
            "backend": "duckdb",
            "row_count": row_count,
            "field_count": len(fields),
            "blank_counts": blank_counts,
            "key_field": key_field,
            "distinct_keys": distinct_keys,
            "duplicate_key_rows": max(0, row_count - distinct_keys)
            if key_index is not None
            else 0,
        }
    finally:
        connection.close()


def profile_dataset(
    fields: list[str], rows: list[dict[str, str]], key_field: str | None = None
) -> dict[str, Any]:
    """Return non-sensitive shape and key-quality metrics for a dataset."""

    if duckdb is None:
        return _python_profile(fields, rows, key_field, "python-fallback")
    if len(rows) > MAX_INLINE_ROWS:
        return _python_profile(fields, rows, key_field, "python-fallback-large-inline")
    try:
        return _duckdb_profile(fields, rows, key_field)
    except Exception:
        # DuckDB is an optimization boundary, not a reason to reject valid input.
        return _python_profile(fields, rows, key_field, "python-fallback-engine-error")
