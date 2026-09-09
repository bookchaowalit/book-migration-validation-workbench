# Data engine boundary

Execution adapter for profiling canonical tabular inputs.

- Uses DuckDB for bounded in-memory profiling in the local V1 flow.
- Falls back to the deterministic Python implementation when DuckDB is not
  installed or the payload is too large for an inline SQL values query.
- Keeps file storage, HTTP, and reconciliation policy outside this package.

The next connector can hand DuckDB a file or Arrow relation directly so large
datasets do not need to be expanded into a Python list first.
