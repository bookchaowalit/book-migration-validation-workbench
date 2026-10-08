---
title: Migration Validation Workbench — Test Strategy และ UAT
doc_id: MVW-DOC-07
doc_type: test-uat
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: QA (Book Dev)
related: 03-nfr-security.md, 05-srs.md, 08-rtm.md
---

# Migration Validation Workbench — Test Strategy และ UAT

## 1. ระดับการทดสอบ

| ระดับ | เครื่องมือ | สถานะ |
|---|---|---|
| Static | ruff `--select F`, `tsc --noEmit` (web) | ใน CI |
| Unit/regression | pytest/unittest ใน `evals/tests/` (56 test function, 9 ไฟล์) | ใน CI |
| API integration | FastAPI `TestClient` (`test_api.py`, ต้องมี httpx; ไม่มีจะ skip) | ใน CI |
| Packaging | สร้าง wheel, ตรวจว่ามี 6 package + sample CSV, ติดตั้ง non-editable แล้วเรียก `/fixtures/*` | ใน CI |
| Web build | `npm ci`, `typecheck`, `build` | ใน CI |
| UI/E2E | ไม่มี (UPGRADE-PLAN P1 เสนอ Playwright/Testing Library) | Gap |
| UAT/operator trial | MVW-123/124: 5 operator กับข้อมูลที่ลบข้อมูลระบุตัวตน | ยังไม่ทำ |

## 2. สภาพแวดล้อม

- CI: GitHub Actions `ubuntu-latest`, Python 3.11, Node 22, timeout 15 นาทีต่อ job, `permissions: contents: read`
- local: Python 3.10+, extra `.[dev,parquet]`; test ไม่ต้องใช้ network
- ข้อมูล test: sample สังเคราะห์ใน `apps/api/src/migration_validation_api/sample_data/` (รวมชุดลูกค้าไทย) และข้อมูลที่สร้างใน test

## 3. Test cases

| TC | อ้าง FR | Test ใน repo | ผลคาดหวัง |
|---|---|---|---|
| TC-01 | FR-01 | `test_csv_is_normalized_with_metadata_and_safe_filename`, `test_xlsx_uses_the_same_canonical_shape`, `test_tsv_and_invalid_format_behavior_are_explicit`, `test_parquet_is_supported_when_optional_runtime_is_available`, `test_malformed_xlsx_is_rejected` | ทุก format ได้ shape เดียวกัน; format ผิด/เสีย ถูกปฏิเสธชัดเจน |
| TC-02 | FR-02 | `test_configuration_fingerprint_is_order_independent` | fingerprint ไม่ขึ้นกับลำดับ key |
| TC-03 | FR-03, FR-18 | `test_health_and_profiles`, `test_inspect_strips_directory_parts_from_filenames` | 200 และชื่อไฟล์ไม่มี path |
| TC-04 | FR-04 | `test_blank_key_is_not_silently_dropped` | key ว่างเป็น `invalid_key` |
| TC-05 | FR-05 | `test_mapping_suggestions_are_bounded`, `test_duplicate_headers_are_rejected`, `test_thai_headers_are_distinct_and_map_exactly` | mapping มีขอบเขต, header ซ้ำ → error, header ไทย map ถูก |
| TC-06 | FR-06 | `test_registry_exposes_only_reviewed_profiles`, `test_thai_customer_profile_normalizes_common_field_shapes`, `test_profile_matches_without_mutating_raw_evidence`, `test_buddhist_era_leap_day_uses_gregorian_calendar`, `test_landline_country_code_and_thai_digits`, `test_zero_width_characters_do_not_break_matches`, `test_unknown_normalization_profile_fails_closed` | normalize ถูกและ raw evidence ไม่ถูกแก้ |
| TC-07 | FR-07 | `test_fixture_produces_explainable_statuses`, `test_match_rate_is_not_100_with_exceptions`, `test_reconcile_with_spaced_and_thai_headers` | 6 สถานะพร้อมเหตุผล |
| TC-08 | FR-08 | `test_fuzzy_candidate_is_advisory_and_never_auto_approved`, `test_fuzzy_configuration_can_be_disabled_and_is_bounded`, `test_fuzzy_candidates_are_symmetric_for_target_only_records` | candidate ไม่ auto-approve |
| TC-09 | FR-09 | `test_review_statuses_are_keyed_to_evidence_and_summarized` | summary ของ review ถูก |
| TC-10 | FR-10 | `test_package_is_stable_and_omits_raw_evidence_values` | package เสถียรและไม่มีค่า raw |
| TC-11 | FR-12 | `test_sql_is_read_only_and_quoted`, `test_real_world_headers_are_quoted_not_rejected`, `test_quote_escaping_prevents_breaking_out_of_identifier`, `test_table_names_stay_strict`, `test_blank_long_or_control_column_names_are_rejected`, `test_generated_sql_executes_and_finds_differences` | SQL ปลอดภัยและรันใน DuckDB ได้ |
| TC-12 | FR-13 | `test_default_profile_selects_pii_like_fields_but_not_generic_ids`, `test_redaction_does_not_mutate_reconciliation_result` | redact ถูก field |
| TC-13 | FR-14 | `test_default_limits_are_documented_values`, `test_csv_row_limit`, `test_column_limit_for_csv_and_tsv`, `test_xlsx_row_limit_fails_while_parsing`, `test_too_large_is_still_a_dataset_input_error`, `test_dataset_shape_limit_returns_413`, `test_size_guard`, `test_column_reference_beyond_excel_limit_is_rejected`, `test_valid_reference_is_accepted`, `test_corrupted_part_is_a_dataset_error` | 413/400 ตามกรณี |
| TC-14 | FR-15 | `test_loopback_hosts_start`, `test_non_loopback_host_is_refused_without_opt_in`, `test_allow_remote_opts_in` | host ไม่ใช่ loopback ถูกปฏิเสธ |
| TC-15 | FR-16 | `test_fixture_route_blocks_traversal`, `test_sample_flow_is_served_from_package_data`, `test_reconcile_with_fixture_files_base64` | sample ใช้ได้, traversal ถูกกัน |
| TC-16 | FR-17 | `test_profile_is_non_sensitive_and_counts_duplicate_keys` | profile ไม่มีค่า raw |
| TC-17 | NFR-08 | `test_cors_allows_only_local_origins` | origin อื่นไม่ได้ header CORS |
| TC-18 | — | `test_bad_inputs_return_structured_errors`, `test_console_script_is_registered` | error เป็น JSON, มี console script |
| TC-19 | FR-11 | ไม่มี | report มีสรุป สถานะ review และ mapping — ต้องเพิ่ม UI test |
| TC-20 | US-12 | ไม่มี test end-to-end แยก | rerun ผ่าน API ได้ผลเท่าเดิม — ครอบคลุมบางส่วนโดย TC-02, TC-10 |

## 4. เกณฑ์ผ่าน (entry/exit)

- Entry operator trial: CI เขียวบน `main`, walkthrough แบบไม่ใช้ข้อมูลจริง (MVW-123) พร้อม, คู่มือ `04-runbook.md` ทดลองติดตั้งบนเครื่องสะอาดผ่าน
- Exit trial (ตาม brief §6): operator ≥ 5 คน, เวลาตรวจลดลง ≥ 50%, exception ที่สุ่มตรวจย้อนกลับได้ทุกกรณี, ไม่มีข้อมูลจริงหลุดใน log/fixture/Git
- Exit pilot: ลูกค้า paid pilot รับ audit package และ report เป็นหลักฐานส่งมอบ **[ต้องยืนยัน]** รูปแบบการลงนาม

## 5. หลักฐานที่มี

ผลรันวันที่ 2026-10-08 บนเครื่องนี้ (ไม่ได้ติดตั้ง package ใด ๆ, ตั้ง `PYTHONPATH` ไปที่ `src/` ของแต่ละ package และ `PYTHONDONTWRITEBYTECODE=1`):

```text
python3 -m unittest discover -s evals/tests
Ran 54 tests in 0.224s
FAILED (errors=1, skipped=13)
```

- 40 test ผ่าน
- 13 skip เพราะเครื่องนี้ไม่มี `fastapi`/`httpx` (test_api) และ/หรือ `pyarrow`
- 1 error: `test_cli_bind` import ไม่ได้เพราะไม่มี `pytest` ในเครื่อง — เป็นข้อจำกัดของสภาพแวดล้อม ไม่ใช่ความล้มเหลวของโค้ด
- `docs/UPGRADE-PLAN.md` บันทึกว่า pass 3 มี 48 test ผ่านใน venv ใหม่ และ CI รันชุดเต็ม; ผล CI ล่าสุดยังไม่ได้ตรวจ **[ต้องยืนยัน]**

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| QA (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `evals/tests/*.py`, `evals/README.md`
- `.github/workflows/ci.yml`, `pyproject.toml`
- `docs/UPGRADE-PLAN.md`
- `(solo-empire) opportunities/business/cli-tools/MIGRATION-VALIDATION-WORKBENCH-PRODUCT-BRIEF.md` §6
