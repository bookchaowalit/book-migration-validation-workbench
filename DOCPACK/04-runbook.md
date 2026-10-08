---
title: Migration Validation Workbench — Runbook การติดตั้งและใช้งาน
doc_id: MVW-DOC-04
doc_type: runbook
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: DevOps / Operator (Book Dev)
related: 02-architecture.md, 03-nfr-security.md, 06-ux-flows.md
---

# Migration Validation Workbench — Runbook การติดตั้งและใช้งาน

## 1. Environments

| Env | รายละเอียด | สถานะ |
|---|---|---|
| local (dev) | editable install + `next dev` | ใช้งานอยู่ |
| local (wheel) | `pip install` จาก wheel + `next build && next start` | CI ตรวจว่า wheel มีครบและเสิร์ฟ sample ได้ |
| CI | GitHub Actions `ubuntu-latest`, Python 3.11, Node 22 | มี workflow; ผลรันล่าสุด **[ต้องยืนยัน]** |
| shared/production | ไม่มี — ต้องผ่าน gate ใน `deploy/README.md` | ไม่ทำ |

## 2. ติดตั้งและรัน

ต้องมี Python 3.10+ และ Node.js 20+

```bash
# จาก root ของ repository
python3 -m pip install -e .                 # เพิ่ม '.[parquet]' ถ้าต้องอ่าน Parquet
migration-workbench                         # หรือ python3 run.py / python3 -m migration_validation_api
```

อีก terminal:

```bash
cd apps/web
npm install
npm run dev                                 # เปิด http://localhost:3000
```

ตัวเลือก CLI: `--host` (ค่าเริ่มต้น `127.0.0.1`), `--port` (`8765`), `--allow-remote` (ห้ามใช้กับข้อมูลจริง)

Build ตรวจก่อนส่งมอบ (เหมือน CI):

```bash
pip install -e ".[dev,parquet]"
ruff check --select F packages connectors apps/api evals run.py
python -m pytest -q
cd apps/web && npm ci && npm run typecheck && npm run build
```

## 3. Config (ชื่อตัวแปรเท่านั้น)

| ตัวแปร | ฝั่ง | ผล |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | web | URL ของ API (ค่าเริ่มต้น `http://127.0.0.1:8765`) |
| `MVW_ALLOWED_ORIGINS` | API | รายการ origin CORS คั่นด้วย comma |
| `MIGRATION_WORKBENCH_FIXTURES` | API | โฟลเดอร์ sample data ทางเลือก |

ไม่มี secret ใดในระบบ

## 4. Health check

- `GET http://127.0.0.1:8765/api/health`
- `GET /api/normalization-profiles` ต้องคืน `generic` และ `thai_customer`
- OpenAPI: `http://127.0.0.1:8765/docs`
- ในเว็บกด `ใช้ข้อมูลตัวอย่าง` แล้วรันได้ผลและ evidence

## 5. Rollback

- เครื่องมือ local: ติดตั้ง commit/wheel ก่อนหน้า (`pip install` เวอร์ชันเดิม) ไม่มี state ให้ย้อน
- audit package เก่ายังใช้ตรวจซ้ำได้ตราบที่ `rule_version` ตรง — ถ้าเปลี่ยน rule ให้บันทึกเวอร์ชันในรายงาน pilot

## 6. Incident/troubleshooting

| อาการ | สาเหตุที่เป็นไปได้ | การแก้ |
|---|---|---|
| `--host ... is not loopback` | ใส่ host ที่ไม่ใช่ 127.0.0.1/localhost/::1 | ใช้ loopback หรือ (เฉพาะ demo ไม่ใช่ข้อมูลจริง) `--allow-remote` |
| 413 | ไฟล์ > 20 MB หรือ > 200,000 แถว / 500 คอลัมน์ | แบ่งไฟล์ |
| 400 "headers must be unique" | header ซ้ำหลัง normalize | แก้ header ต้นทาง |
| Parquet ใช้ไม่ได้ | ไม่ได้ติดตั้ง extra `parquet` | `pip install -e '.[parquet]'` |
| เว็บเรียก API ไม่ได้ (CORS) | web ไม่ได้รันที่ localhost:3000 | ตั้ง `MVW_ALLOWED_ORIGINS` |
| import error หลังติดตั้ง | `.venv` เก่าที่ editable mapping ว่าง (UPGRADE-PLAN pass 3) | สร้าง venv ใหม่ |
| review หายหลังปิดหน้า | review อยู่ใน state ของ browser | ดาวน์โหลด report/audit ก่อนปิด |

## 7. Backup/restore

ไม่มีข้อมูลถาวร เก็บไฟล์ input ต้นฉบับ + audit package + report ไว้ในที่เก็บของงาน pilot ตามข้อตกลงกับลูกค้า **[ต้องยืนยัน]**

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Operator (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`, `apps/api/README.md`, `deploy/README.md`, `docs/UPGRADE-PLAN.md`
- `apps/api/src/migration_validation_api/cli.py`, `apps/api/src/migration_validation_api/server.py`
- `apps/web/app/page.tsx`, `.github/workflows/ci.yml`, `pyproject.toml`
