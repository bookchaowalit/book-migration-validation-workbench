# Upgrade Plan

**Current state: 8/10** (pass 3: 7.5 -> 8) — solid deterministic reconciliation core with
privacy/audit packages, properly packaged (console script, wheel checked in
CI), bounded inputs, API + web tested/built in CI; no persistence, auth or
real DB connectors yet (by design for V1).

## Backlog

### P0
- (none open)

### P1
- CSV rows are fully parsed before the row cap is checked (20 MB body bounds
  it today); stream-count in `read_csv_text` if the body limit is raised.
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

## Done in this pass (pass 2)
- Packaging: `pyproject.toml` now installs all six packages via explicit
  `package-dir` mapping (monorepo `src/` trees); new
  `migration_validation_api.cli` + `__main__`, console script
  `migration-workbench`; `run.py` is a thin wrapper. Every `sys.path.insert`
  removed from tests and entry points. CI builds the wheel, asserts every
  package is inside, and starts the console script.
- Fixture root overridable with `MIGRATION_WORKBENCH_FIXTURES`.
- Input shape caps: 200,000 data rows / 500 columns per dataset
  (`DatasetTooLarge` → HTTP 413 on `/api/inspect` and `/api/reconcile`);
  XLSX stops parsing as soon as the row cap is crossed.
- Tests 40 → 47; verified in a fresh venv (editable + wheel), server
  `/api/health` smoke via the console script; ruff 0.16.9 `--select F` clean.

## Done in this pass (pass 3)
- Sample datasets moved from `evals/fixtures/` into the API package
  (`migration_validation_api/sample_data/`, declared as setuptools
  package data); `FIXTURE_ROOT` defaults to it, so "ใช้ข้อมูลตัวอย่าง" works
  from a wheel / non-editable install. `MIGRATION_WORKBENCH_FIXTURES` still
  overrides.
- Tests load samples via `importlib.resources`; traversal test now targets
  `../server.py` (a real sibling file of the sample root). New test asserts
  the sample flow bytes come from package data. 47 -> 48 tests.
- CI asserts the wheel contains the sample CSVs and serves `/fixtures/*`
  from a fresh non-editable venv outside the checkout (verified locally).
- Note: a stale local `.venv` produced an empty editable-finder mapping;
  a fresh venv installs correctly (recreate `.venv` if imports fail).
- Thai / Unicode reconciliation bugs: `normalize_header` kept only ASCII, so
  every Thai header normalized to "" — a CSV with two Thai headers was
  rejected as "headers must be unique" and `suggest_mapping` auto-selected
  "ชื่อ" -> "ที่อยู่" at confidence 1.0. Headers/tokens now keep letters, marks
  and digits of every script (NFKC + casefold). Thai-customer profile: the
  Buddhist-era offset is applied before date validation (29/02/2567 was left
  raw and 29/02/2568 became the impossible 2025-02-29); +66 landlines
  (10 digits) map to 0x; Thai digits in phone/tax ID/date; zero-width
  characters no longer break equality. `match_rate` never shows 100.0 with
  exceptions (`_display_rate`). Tests in `test_normalization.py` and
  `test_reconcile.py`.
