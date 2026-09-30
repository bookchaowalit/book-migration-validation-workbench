# Upgrade Plan

**Current state: 7/10** — solid deterministic reconciliation core with
privacy/audit packages, API + web now tested/built in CI; no persistence,
auth or real DB connectors yet (by design for V1).

## Backlog

### P0
- (none open)

### P1
- `pyproject.toml` declares `packages = []`, so `pip install -e .` installs
  deps only and every entry point/test patches `sys.path`. Package the
  `src/` trees properly (or a workspace) and drop the path hacks.
- Row/column caps for inputs (e.g. 200k rows) with a clear 413-style error;
  today only the 20 MB body and XLSX part size are bounded.
- Web: add Playwright or Testing Library smoke test for the sample flow
  (load sample → run → evidence table keyboard selection).

### P2
- Validate `review_statuses` keys against evidence ids and cap its size.
- Move `fastapi.testclient` usage to `httpx2` when Starlette drops httpx.
- Generated SQL dialect notes (DuckDB/Postgres tested; others untested).

## Done in this pass (2026-09-30)
- Bug: any mapped column with a space, Thai text or other non-identifier
  header made `/api/reconcile` fail with 400 (strict identifier rule applied
  to CSV headers). Columns are now delimited identifiers with `"` escaping;
  table names stay strict. Verified by executing the SQL in DuckDB.
- Security: XLSX cell references beyond Excel's 16,384 columns
  (`ZZZZZZZ1`) could allocate billions of cells; parts larger than 100 MB
  decompressed are rejected (zip bomb); CRC failures map to a 400 error.
- New tests: `evals/tests/test_sql_generation.py`,
  `evals/tests/test_api.py` (health, fixture traversal, reconcile, errors,
  size guard, CORS, XLSX hardening). 24 → 40 tests.
- Web a11y: labels for mapping/filter/search controls; evidence rows are
  keyboard-selectable (Enter/Space) with `aria-current`.
- CI: ruff + pytest, and web `npm ci`/typecheck/build. `dev` extra added.
