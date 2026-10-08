---
title: Migration Validation Workbench — Product Card
doc_id: CARD-book-migration-validation-workbench
doc_type: product-card
verdict: invest
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# Migration Validation Workbench — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

ช่วยทีม Data/IT และผู้ให้บริการ migration ของ SME เทียบข้อมูลระบบเก่ากับระบบใหม่ แล้วได้รายงานที่บอกว่าอะไรตรง หาย ซ้ำ หรือผิด พร้อมหลักฐานที่ตรวจซ้ำได้ โดยข้อมูลไม่ออกนอกเครื่อง

## 2. ปัญหาและผู้ใช้เป้าหมาย

- ปัญหา: หลัง migration ทีมต้องพิสูจน์ความครบถ้วนและความถูกต้องของข้อมูล มักใช้ Excel เทียบมือซึ่งตรวจซ้ำไม่ได้
- ผู้ใช้ (ตาม product brief): Data/IT operator, ผู้ให้บริการ migration สำหรับ SME, agency ที่ต้องส่งรายงานลูกค้า, เจ้าของกิจการที่เทียบ Excel/CSV

## 3. สิ่งที่ทำได้จริงตอนนี้

- API FastAPI (`/api/health`, `/api/inspect`, `/api/reconcile`, `/api/normalization-profiles`) bind loopback โดยค่าเริ่มต้น + web Next.js
- รับ CSV/TSV/XLSX/Parquet เข้า canonical contract พร้อม input SHA-256
- ผลตรวจ `match`, `value_mismatch`, `missing_target`, `missing_legacy`, `duplicate`, `invalid_key`; fuzzy candidate ไม่ auto-approve
- normalization `generic`/`thai_customer` (ชื่อไทย เบอร์ เลขภาษี วันที่), review queue, audit package แบบ deterministic, Markdown report, SQL export
- eval tests ครอบคลุม reconcile, redaction, normalization, SQL generation

## 4. หลักฐานสถานะ

| รายการ | ค่า (ตรวจจาก repository) |
|---|---|
| Stack | FastAPI, Python |
| Commits | 10 (แรก 2026-09-09 → ล่าสุด 2026-10-01) |
| Source | 29 ไฟล์ / 3,091 บรรทัด |
| Tests | 9 ไฟล์ |
| CI | 1 workflow |
| Deploy config | ไม่มี |
| Live URL | ไม่มี |
| README | 138 บรรทัด (`Migration Validation Workbench`) |
| โครงสร้างซ้ำ (template family) | 1 repo ที่มี structure signature เดียวกัน |

product brief อยู่ใน `opportunities/business/cli-tools/` สถานะ "Draft for paid-pilot validation"

## 5. คุณค่าและจุดต่าง

- จุดต่าง: local-first (ไม่ส่งข้อมูลลูกค้าให้ LLM), normalization ภาษาไทย, audit package ที่ไม่มี raw values และ human-in-the-loop — ตรงกับงานที่ต้องส่งมอบหลักฐานให้ลูกค้า
- ต่อยอดจากประสบการณ์งาน migration ฐานข้อมูลของลูกค้า (เช่น `clients/oak/azure-migration-database-design`) **[สมมติฐาน]** ว่าใช้กับงานนั้นได้
- มุมรายได้: paid pilot / บริการตรวจ migration ต่องาน **[สมมติฐาน]** — ยังไม่มีผู้จ่าย

## 6. ช่องว่างสำคัญ

- ยังไม่มี operator trial 5 คนและ paid pilot ตาม decision gate ใน brief
- ไม่มี auth, ไม่มี deploy, ไม่ต่อ database จริง, review queue อยู่ใน memory
- ยังไม่มี live demo ให้ผู้ซื้อลองเอง

## 7. คำตัดสิน

**`invest`** — แก้ปัญหาจริงที่มีผู้ซื้อชัด (งาน migration) มี core ที่ทำงานและทดสอบแล้ว และมี product brief พร้อม decision gate จึงควรต่อยอด จะลดเป็น `showcase` ถ้าหลัง trial 5 คนไม่มีข้อเสนอ paid pilot แม้แต่งานเดียว

## 8. ขั้นต่อไป

1. เลื่อนเป็น docpack L1 (PRD + architecture) ตามมาตรฐาน
2. ทำ operator trial 5 คนด้วยข้อมูลตัวอย่างไทยตาม brief แล้วบันทึกผล
3. เตรียม demo ที่รันได้ในเครื่องผู้ซื้อ (installer/คู่มือหน้าเดียว) ก่อนเสนอ paid pilot

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `apps/api/src/migration_validation_api/server.py`
- `evals/tests/`
- `(solo-empire) opportunities/business/cli-tools/MIGRATION-VALIDATION-WORKBENCH-PRODUCT-BRIEF.md`
- `(solo-empire) plans/decision-context/MIGRATION-VALIDATION-WORKBENCH-V1.1.md`
