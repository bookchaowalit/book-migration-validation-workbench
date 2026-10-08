---
title: Migration Validation Workbench — Product Requirements (PRD)
doc_id: MVW-DOC-01
doc_type: prd
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
related: 00-overview.md, 00-product-card.md, 05-srs.md, 08-rtm.md
---

# Migration Validation Workbench — Product Requirements (PRD)

> PRD นี้สรุปจาก product brief (`Draft for paid-pilot validation`) และแผน V1.1 ที่ root ของ Solo Empire แล้วตรวจเทียบกับโค้ดจริง ผลิตภัณฑ์ระยะยาวตาม brief คือ "Business Data Operator"

## 1. ปัญหาและเป้าหมาย

### 1.1 ปัญหา

| # | ปัญหา | ผลกระทบ |
|---|---|---|
| PB-1 | หลัง migration ต้องพิสูจน์ว่าข้อมูลครบและถูก มักเทียบด้วย Excel/script มือ | ตรวจซ้ำไม่ได้ ใช้เวลานาน |
| PB-2 | exception (หาย ซ้ำ ค่าไม่ตรง) ไม่มีเหตุผลที่ย้อนกลับถึง row/field/rule ได้ | ส่งมอบลูกค้าไม่ได้อย่างมั่นใจ |
| PB-3 | ข้อมูลลูกค้าเป็นความลับ ส่งขึ้น SaaS/LLM ไม่ได้ | เครื่องมือ cloud ใช้ไม่ได้ |
| PB-4 | ข้อมูลไทย (ชื่อ เบอร์ เลขภาษี วันที่ พ.ศ.) มีรูปแบบหลากหลาย | เทียบตรงตัวแล้วได้ mismatch ปลอม |

### 1.2 เป้าหมาย (ตาม brief §6)

| ID | Metric | Pass signal |
|---|---|---|
| G-1 Operator trial | จำนวน operator ที่ทดลองกับข้อมูลที่ลบข้อมูลระบุตัวตนแล้ว | ≥ 5 คน |
| G-2 เวลา | เวลาตรวจเทียบ workflow เดิม | ลดลง ≥ 50% |
| G-3 Explainability | exception ที่สุ่มตรวจย้อนกลับไป row, field, rule ได้ | ทุกกรณี |
| G-4 Commercial | paid pilot ก่อนเพิ่ม production database connector | ≥ 1 งาน |

ปัจจุบันยังไม่มีผลวัด G-1 ถึง G-4 (งาน `MVW-123` ถึง `MVW-125` ยังไม่ทำ)

## 2. ผู้ใช้/persona

| ID | Persona | งานหลัก |
|---|---|---|
| P-OPR | Data/IT operator | โหลด export สองฝั่ง เลือก key ตรวจ ส่ง report |
| P-MIG | ผู้ให้บริการ migration สำหรับ SME | ใช้ audit package เป็นหลักฐานส่งมอบ |
| P-AGY | agency | ส่งรายงานให้ลูกค้า (ใช้ redacted export) |
| P-BIZ | เจ้าของกิจการ | เทียบไฟล์ Excel/CSV ระหว่างระบบ |

## 3. ขอบเขต

### In scope (V1 + V1.1 ที่มีโค้ดแล้ว)

- รับ CSV/TSV/XLSX/Parquet เข้า canonical contract `mvw.input.v1` + SHA-256
- เลือก key, heuristic field mapping พร้อม confidence
- normalization profile `generic` และ `thai_customer`
- reconciliation 6 สถานะ + fuzzy candidate แบบ review-only
- evidence drill-down, review `approved`/`rejected`/`needs-review`
- audit package `mvw.audit.v1`, Markdown report, SQL ตรวจซ้ำ, redacted export
- sample data สังเคราะห์ในตัว package

### Out of scope (brief §8 และ README)

- เชื่อม/เขียนกลับ production database, connector ฐานข้อมูล
- auth, multi-tenant SaaS, เก็บไฟล์ถาวร
- ส่งข้อมูลไป LLM/บริการภายนอก, สรุปสาเหตุด้วย AI
- generic chatbot/file search

## 4. ฟีเจอร์หลักและลำดับความสำคัญ

| ID | ฟีเจอร์ | Priority | สถานะ | แผน |
|---|---|---|---|---|
| F-01 | Canonical input หลาย format + fingerprint | Must | Done | MVW-101, MVW-102 |
| F-02 | Deterministic reconciliation 6 สถานะ | Must | Done | V1 |
| F-03 | Evidence ราย record + reason | Must | Done | V1 |
| F-04 | Redacted export | Must | Done | MVW-103 |
| F-05 | Fixture ไทย/malformed | Must | Done | MVW-104 |
| F-06 | Normalization profiles | Should | Done | MVW-111 |
| F-07 | Conservative fuzzy matching | Should | Done | MVW-112 |
| F-08 | Review queue | Should | Done | MVW-113 |
| F-09 | Audit package | Should | Done | MVW-114 |
| F-10 | Connector-level Excel/Parquet adapters | Could | Open | MVW-121 |
| F-11 | Profile templates (customer, invoice, transaction, product) | Could | Open | MVW-122 |
| F-12 | Operator walkthrough + trial 5 คน | Must (ทางธุรกิจ) | Open | MVW-123, MVW-124 |
| F-13 | เสนอ paid pilot | Must (ทางธุรกิจ) | Open | MVW-125 |

## 5. ตัวชี้วัดความสำเร็จ

- G-1 ถึง G-4 ข้างต้น
- คุณภาพ: acceptance examples ใน brief (key ซ้ำไม่ถูกนับเป็น match, ค่าต่างเป็น `value_mismatch`, record หายเป็น `missing_target`, mapping confidence ต่ำไม่ถูกเลือกอัตโนมัติ, rerun ได้ผลเท่าเดิม) มี test ครอบคลุม — ดู `08-rtm.md`

## 6. Roadmap/phase

```mermaid
flowchart LR
  A["P0 input safety (เสร็จ)"] --> B["P1 review quality (เสร็จ)"]
  B --> C["operator trial 5 คน"]
  C --> D["paid pilot 1 งาน"]
  D --> E["P2 connectors / SaaS decision"]
```

## 7. ข้อสมมติฐานและความเสี่ยง

| ID | รายการ | ประเภท |
|---|---|---|
| A-1 | ผู้ให้บริการ migration ที่ใช้ spreadsheet/script จะยอมใช้ถ้าลดเวลาได้ชัดและส่งมอบ evidence ได้ (brief §9) | **[สมมติฐาน]** |
| A-2 | ใช้กับงาน migration ฐานข้อมูลของลูกค้าที่มีอยู่ได้ | **[สมมติฐาน]** |
| A-3 | มุมรายได้: paid pilot / บริการตรวจ migration ต่องาน | **[สมมติฐาน]** |
| R-1 | ผู้ซื้อต้องติดตั้ง Python + Node เอง — ไม่มี installer หรือ demo ออนไลน์ | ความเสี่ยงการขาย |
| R-2 | review status อยู่ใน state ของ browser เท่านั้น ปิดหน้าแล้วหาย (export ได้ผ่าน audit/report) | ความเสี่ยงการใช้งาน |
| R-3 | ขนาดข้อมูลจำกัด 20 MB / 200,000 แถว / 500 คอลัมน์ ต่อ dataset | ความเสี่ยงกับ migration ขนาดใหญ่ |

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |
| Venture owner (ผู้ตัดสินใจตาม brief) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`, `docs/UPGRADE-PLAN.md`
- `apps/api/src/migration_validation_api/server.py`, `connectors/file-input/src/migration_input/input_contract.py`
- `(solo-empire) opportunities/business/cli-tools/MIGRATION-VALIDATION-WORKBENCH-PRODUCT-BRIEF.md`
- `(solo-empire) plans/decision-context/MIGRATION-VALIDATION-WORKBENCH-V1.1.md`
- `DOCPACK/00-product-card.md`
