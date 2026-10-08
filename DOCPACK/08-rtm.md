---
title: Migration Validation Workbench — Requirements Traceability Matrix
doc_id: MVW-DOC-08
doc_type: rtm
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: BA + QA (Book Dev)
related: 05-srs.md, 06-ux-flows.md, 07-test-uat.md
---

# Migration Validation Workbench — Requirements Traceability Matrix

สถานะหลักฐาน: **Tested** = มี test ใน repo ที่รันใน CI, **Tested (local)** = ยืนยันผ่านจากการรันรอบนี้ด้วย, **Code** = มีโค้ดไม่มี test, **Gap** = ยังไม่ทำ

## 1. ตาราง FR ↔ US ↔ หน้าจอ ↔ TC

| FR | US | Screen | แผน V1.1 | TC | สถานะหลักฐาน |
|---|---|---|---|---|---|
| FR-01 | US-01 | SCR-02 | MVW-101 | TC-01 | Tested (local, ยกเว้น Parquet ที่ skip) |
| FR-02 | US-01, US-12 | SCR-02, SCR-05 | MVW-102 | TC-02 | Tested (local) |
| FR-03 | US-01 | SCR-02 | MVW-101 | TC-03 | Tested (CI; local skip เพราะไม่มี fastapi) |
| FR-04 | US-02 | SCR-02 | V1 | TC-04 | Tested (local) |
| FR-05 | US-03 | SCR-03 | V1 | TC-05 | Tested (local) |
| FR-06 | US-04 | SCR-02 | MVW-111 | TC-06 | Tested (local) |
| FR-07 | US-05 | SCR-04, SCR-05 | V1 | TC-07 | Tested (local) |
| FR-08 | US-07 | SCR-02, SCR-06 | MVW-112 | TC-08 | Tested (local) |
| FR-09 | US-08 | SCR-06 | MVW-113 | TC-09 | Tested (local) |
| FR-10 | US-09 | SCR-05 | MVW-114 | TC-10 | Tested (local) |
| FR-11 | US-09 | SCR-05 | V1 | TC-19 | Code (web, ไม่มี test) |
| FR-12 | US-09 | SCR-05 | V1 | TC-11 | Tested (local) |
| FR-13 | US-10 | — (อยู่ใน response `redacted_export`) | MVW-103 | TC-12 | Tested (local) |
| FR-14 | — | SCR-02 (ข้อความ error) | V1.1 | TC-13 | Tested (บางส่วน local, API ใน CI) |
| FR-15 | — | — (CLI) | V1.1 | TC-14 | Tested (CI; local import error เพราะไม่มี pytest) |
| FR-16 | US-11 | SCR-02 | V1.1 | TC-15 | Tested (CI) |
| FR-17 | — | — | V1.1 | TC-16 | Tested (local) |
| FR-18 | — | SCR-07 | V1.1 | TC-03 | Tested (CI) |
| FR-19 | — | — | MVW-122 | — | Gap |
| FR-20 | — | — | MVW-121 | — | Gap |

## 2. Acceptance examples ของ product brief ↔ หลักฐาน

| Acceptance example (brief §6) | TC |
|---|---|
| key ซ้ำต้องไม่ถูกนับเป็น match เงียบ ๆ | TC-07 (`test_fixture_produces_explainable_statuses`), TC-16 |
| ค่า field ที่ต่างกันต้องเป็น `value_mismatch` | TC-07 |
| record ที่หายจาก target ต้องเป็น `missing_target` | TC-07 |
| mapping confidence ต่ำต้องไม่ถูกเลือกอัตโนมัติ | TC-05 **[ต้องยืนยัน]** ว่ามี assertion เรื่อง threshold โดยตรง |
| input และ configuration เดิม rerun แล้วได้ผลเท่าเดิม | TC-02, TC-10 (ยังไม่มี test rerun end-to-end) |

## 3. ช่องว่างที่ยังไม่ครอบคลุม

1. ไม่มี UI/E2E test — FR-11 (report) และ flow บนหน้าเว็บทั้งหมดไม่มีหลักฐานอัตโนมัติ
2. ไม่มี test rerun end-to-end ผ่าน API ที่ยืนยันผลเท่ากันทุก field
3. metric ธุรกิจ G-1 ถึง G-4 ยังไม่มีข้อมูล (operator trial/pilot ยังไม่เริ่ม)
4. ป้าย "field-profile redacted" ใน report ขัดกับการแสดงค่า key ดิบ (R-06 ใน `03-nfr-security.md`)
5. FR-19, FR-20 ยังไม่เริ่ม

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| BA (Book Dev) | รอพิจารณา | — | ________ |
| QA (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `05-srs.md`, `06-ux-flows.md`, `07-test-uat.md`
- `evals/tests/*.py`, `.github/workflows/ci.yml`
- `(solo-empire) opportunities/business/cli-tools/MIGRATION-VALIDATION-WORKBENCH-PRODUCT-BRIEF.md`
- `(solo-empire) plans/decision-context/MIGRATION-VALIDATION-WORKBENCH-V1.1.md`
