# Migration Validation Workbench

ตรวจข้อมูลหลัง migration แล้วบอกให้รู้ว่าอะไรตรง อะไรหาย อะไรซ้ำ และค่าไหนไม่ตรงกัน

นี่คือ V1 แบบ local-first สำหรับพิสูจน์ workflow ก่อนเชื่อมต่อฐานข้อมูลจริงหรือทำ SaaS เต็มรูปแบบ

## Technology boundaries

```text
apps/web                  Next.js App Router + TypeScript browser UI
apps/api                  FastAPI + Pydantic HTTP transport and orchestration
packages/reconciliation-core
                          deterministic reconciliation rules
packages/data-engine     DuckDB profiling adapter
packages/privacy         redacted export helpers
packages/audit           deterministic, privacy-safe audit package
packages/contracts       versioned JSON response schema
connectors/file-input    CSV/TSV/XLSX/Parquet → canonical dataset
evals                     sanitized fixtures and regression tests
deploy                    future runtime/deployment controls
```

ทุก boundary อยู่ใน product repo เดียวกันในระยะ V1 แต่มี ownership และ contract แยกชัดเจน เพื่อแยกเป็นหลาย Git repositories ได้ภายหลังโดยไม่ต้องย้าย business logic แบบฉุกละหุก

เอกสารผลิตภัณฑ์:

- [Product brief](../../../../../../../../../opportunities/business/cli-tools/MIGRATION-VALIDATION-WORKBENCH-PRODUCT-BRIEF.md)
- [V1.1 plan](../../../../../../../../../plans/decision-context/MIGRATION-VALIDATION-WORKBENCH-V1.1.md)

## สิ่งที่ทำได้

- รับ CSV, XLSX หรือ Parquet ของระบบเก่าและระบบใหม่
- แปลงทุก format เข้า canonical input contract เดียวกัน พร้อม input SHA-256 fingerprint
- เลือก key ของแต่ละ dataset
- เลือก normalization profile แบบ `generic` หรือ `thai_customer` ก่อนตรวจ
- แนะนำ field mapping ด้วย heuristic ที่ตรวจสอบได้
- แสดง fuzzy candidates แบบ bounded พร้อม score/เหตุผล โดยไม่ auto-approve
- ตรวจ `match`, `value_mismatch`, `missing_target`, `missing_legacy`, `duplicate` และ `invalid_key`
- เปิดดู evidence ราย record
- mark evidence เป็น `Approve`, `Reject` หรือ `Needs review` และส่งสถานะต่อในการ rerun/report
- ดาวน์โหลด JSON audit package, Markdown report และ SQL สำหรับตรวจซ้ำ

## ขอบเขต V1.1 ที่เพิ่มแล้ว

- `/api/inspect` สำหรับตรวจ fields และ metadata ก่อนเริ่ม reconciliation
- `/api/normalization-profiles` สำหรับดู profile ที่รองรับ
- normalization profiles แบบ conservative สำหรับชื่อไทย, เบอร์โทร, เลขภาษี, วันที่ และที่อยู่ โดย raw evidence ไม่ถูกแก้
- configuration fingerprint สำหรับ key, mapping, table และ contract version
- field-profile redacted export สำหรับ demo/pilot
- configurable fuzzy review threshold และ candidate limit โดยยังคงให้คนอนุมัติเอง
- review queue แบบ in-memory ที่ไม่เขียนกลับ source
- audit package แบบ deterministic ที่เก็บ rule/config/fingerprint/summary และ row references โดยไม่ใส่ raw values
- fixture และ test coverage สำหรับชื่อไทย, XLSX, Parquet (เมื่อมี optional runtime) และ malformed input

## สิ่งที่ยังไม่ทำ

- ไม่เชื่อมต่อ production database
- ไม่เก็บไฟล์ upload ถาวร
- ไม่ส่งข้อมูลออกไปยัง LLM หรือบริการภายนอก
- ไม่สรุปสาเหตุด้วย AI; reason ที่แสดงเป็น deterministic rule

## เริ่มใช้งาน

ต้องใช้ Python 3.10+ และ Node.js 20+; CSV/XLSX ใช้ standard library ได้ ส่วน Parquet ต้องมี PyArrow

ติดตั้ง optional Parquet runtime เมื่อจำเป็น:

```bash
python3 -m pip install -e '.[parquet]'
```

```bash
cd projects/product/engineering/book-dev/github/bookchaowalit/book-apps/tools/book-migration-validation-workbench
python3 -m pip install -e .
migration-workbench            # หรือ python3 run.py / python3 -m migration_validation_api
```

`pip install -e .` ติดตั้งทุก package ใน monorepo (`reconciliation_core`,
`migration_data_engine`, `migration_input`, `migration_privacy`,
`migration_audit`, `migration_validation_api`) จาก `src/` ของแต่ละโฟลเดอร์
จึงไม่ต้องแก้ `sys.path`; ถ้าติดตั้งแบบ non-editable ให้ตั้ง
`MIGRATION_WORKBENCH_FIXTURES=<repo>/evals/fixtures` เพื่อให้ปุ่มข้อมูลตัวอย่างใช้งานได้

เปิดอีก terminal แล้วรัน:

```bash
cd projects/product/engineering/book-dev/github/bookchaowalit/book-apps/tools/book-migration-validation-workbench/apps/web
npm install
npm run dev
```

เปิด <http://localhost:3000> แล้วกด `ใช้ข้อมูลตัวอย่าง` ได้ทันที

รัน test:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,parquet]"
python3 -m unittest discover -s evals/tests -v   # หรือ python -m pytest -q
```

ขนาด input: body ไม่เกิน 20 MB และแต่ละ dataset ไม่เกิน 200,000 แถว / 500
คอลัมน์ (เกินแล้วได้ HTTP 413 พร้อมข้อความ error)

API tests (`evals/tests/test_api.py`) ใช้ FastAPI `TestClient` ซึ่งต้องมี
`httpx`; ถ้าไม่มีจะ skip อัตโนมัติ CI (`.github/workflows/ci.yml`) รัน ruff,
Python tests และ `npm ci` + `typecheck` + `build` ของ `apps/web` ทุกครั้งที่ push

Generated SQL: ชื่อตารางต้องเป็น identifier แบบ strict (`schema.table`) แต่ชื่อ
column มาจาก header จริง จึง quote เป็น delimited identifier (รองรับช่องว่าง/ภาษาไทย,
escape `"` เป็น `""`, ปฏิเสธ control character และยาวเกิน 128 ตัวอักษร)

## Flow ของข้อมูล

```text
Native file bytes in browser
  → Next.js client
  → FastAPI POST /api/inspect (fields + metadata only)
  → POST /api/reconcile (in memory)
  → packages/data-engine (DuckDB profile)
  → packages/reconciliation-core
  → deterministic mapping + reconciliation
  → summary / evidence / fingerprints / generated SQL / audit package
  → report และ audit package download โดยผู้ใช้สั่งเอง
```

ไฟล์ตัวอย่างเป็นข้อมูลสมมติเท่านั้น ห้ามใส่ข้อมูลลูกค้าจริงใน fixture, logs หรือ commit ลง repository

## เกณฑ์พิสูจน์ตลาดรอบถัดไป

1. ให้ data/IT operator 5 คนลองกับ export ที่ลบข้อมูลระบุตัวตนแล้ว
2. จับเวลางานตรวจแบบเดิมเทียบกับ workbench
3. ขอ paid pilot หนึ่ง migration ก่อนเพิ่ม database connector, auth หรือ AI mapping
