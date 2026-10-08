---
title: Migration Validation Workbench — ภาพรวมระบบและสารบัญเอกสาร
doc_id: MVW-DOC-00
doc_type: overview
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
related: 00-product-card.md, 01-prd.md, 02-architecture.md, 03-nfr-security.md, 04-runbook.md, 05-srs.md, 06-ux-flows.md, 07-test-uat.md, 08-rtm.md
---

# Migration Validation Workbench — ภาพรวมระบบและสารบัญเอกสาร

## 1. สรุประบบ

Migration Validation Workbench (MVW) คือเครื่องมือแบบ local-first ที่รับไฟล์ข้อมูลจากระบบเก่า (legacy) และระบบใหม่ (target) ในรูปแบบ CSV/TSV/XLSX/Parquet แล้วตรวจเทียบราย record ด้วยกฎ deterministic จัดผลเป็น `match`, `value_mismatch`, `missing_target`, `missing_legacy`, `duplicate`, `invalid_key` พร้อม evidence ราย record, fuzzy candidate ที่ต้องให้คนอนุมัติ, review queue, audit package ที่ไม่มีค่า raw, Markdown report และ SQL สำหรับตรวจซ้ำ ข้อมูลประมวลผลใน memory บนเครื่องผู้ใช้และไม่ถูกส่งไปบริการภายนอก ประกอบด้วย API FastAPI (`127.0.0.1:8765`) และเว็บ Next.js (`localhost:3000`) ใน monorepo เดียว

## 2. สถานะปัจจุบัน

| รายการ | สถานะ (ตรวจจาก repository 2026-10-08) |
|---|---|
| ระยะ | Local prototype → operator validation / paid-pilot validation (product brief) |
| เวอร์ชัน | `0.2.0` (`pyproject.toml`), audit schema `mvw.audit.v1`, input contract `mvw.input.v1` |
| Commits | 10 (2026-09-09 → 2026-10-01) |
| Test | 56 test function ใน 9 ไฟล์ `evals/tests/`; รันรอบนี้ 40 ผ่าน, 13 skip, 1 import error (ขาด pytest/fastapi ในเครื่อง) — ดู `07-test-uat.md` |
| CI | `.github/workflows/ci.yml`: ruff, pytest, ตรวจ wheel, web typecheck + build |
| Deploy | ไม่มี — local-only (`deploy/README.md`) |
| ผู้ใช้/รายได้ | ยังไม่มี operator trial และ paid pilot |
| คำตัดสิน product card | `invest` |

## 3. ผู้ใช้หลัก

| ผู้ใช้ | งาน |
|---|---|
| Data/IT operator | ตรวจความครบถ้วนหลัง migration และส่งหลักฐาน |
| ผู้ให้บริการ migration สำหรับ SME / agency | ส่งรายงานให้ลูกค้าแบบตรวจซ้ำได้ |
| เจ้าของกิจการ | เทียบ Excel/CSV ระหว่างระบบ |

## 4. ตารางรายการเอกสาร

| รหัส | ไฟล์ | ชื่อ | ผู้อ่านหลัก |
|---|---|---|---|
| CARD-book-migration-validation-workbench | `00-product-card.md` | Product Card (คำตัดสิน invest) | Product owner |
| MVW-DOC-00 | `00-overview.md` | ภาพรวมระบบและสารบัญ | ทุกคน |
| MVW-DOC-01 | `01-prd.md` | Product Requirements (PRD) | Product, ผู้ซื้อ pilot |
| MVW-DOC-02 | `02-architecture.md` | System Architecture | Architect, Dev |
| MVW-DOC-03 | `03-nfr-security.md` | NFR และความปลอดภัย | Architect, Security |
| MVW-DOC-04 | `04-runbook.md` | Runbook การติดตั้งและใช้งาน | Operator |
| MVW-DOC-05 | `05-srs.md` | Software Requirements (SRS) | BA, Dev |
| MVW-DOC-06 | `06-ux-flows.md` | User Flow และ Screen Inventory | UX, QA |
| MVW-DOC-07 | `07-test-uat.md` | Test Strategy และ UAT | QA |
| MVW-DOC-08 | `08-rtm.md` | Requirements Traceability Matrix | BA, QA |

## 5. วิธีอ่าน

1. ผู้ตัดสินใจเชิงธุรกิจ: `00-product-card.md` → `01-prd.md` (decision gate และ metric มาจาก product brief)
2. ผู้พัฒนา: `02-architecture.md` → `05-srs.md` → `08-rtm.md`
3. ผู้ทดลองใช้/operator: `04-runbook.md` และ `06-ux-flows.md`
4. ก่อนใช้กับข้อมูลลูกค้าจริงหรือเปิดให้เครื่องอื่นเข้าถึง: `03-nfr-security.md`

ป้ายกำกับ: **[ต้องยืนยัน]** = ข้อเท็จจริงที่เจ้าของต้องยืนยัน, **[สมมติฐาน]** = สมมติฐานทำงาน

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `DOCPACK/00-product-card.md`, `README.md`, `docs/UPGRADE-PLAN.md`, `deploy/README.md`
- `pyproject.toml`, `.github/workflows/ci.yml`, `evals/tests/`
- `(solo-empire) opportunities/business/cli-tools/MIGRATION-VALIDATION-WORKBENCH-PRODUCT-BRIEF.md`
- `(solo-empire) plans/decision-context/MIGRATION-VALIDATION-WORKBENCH-V1.1.md`
- `git log`
