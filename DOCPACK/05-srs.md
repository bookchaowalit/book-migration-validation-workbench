---
title: Migration Validation Workbench — Software Requirements (SRS)
doc_id: MVW-DOC-05
doc_type: srs
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: BA (Book Dev)
related: 01-prd.md, 06-ux-flows.md, 07-test-uat.md, 08-rtm.md
---

# Migration Validation Workbench — Software Requirements (SRS)

## 1. บทบาทและสิทธิ์

| บทบาท | สิทธิ์ | กลไก |
|---|---|---|
| Operator บนเครื่อง | ทุกฟังก์ชัน | ไม่มี auth; เข้าถึงได้เพราะอยู่บนเครื่องเดียวกัน (loopback) |
| ผู้ตรวจรับ (ลูกค้าของ operator) | อ่าน report/audit package ที่ได้รับ | ไม่ได้ใช้ระบบโดยตรง |
| ผู้ใช้จากเครื่องอื่น | ไม่มีสิทธิ์ | ถูกกันด้วย loopback bind + CORS เว้นแต่ `--allow-remote` |

ระบบไม่มีการแยกบทบาทภายใน (เช่น ผู้ตรวจ vs ผู้อนุมัติ) **[ต้องยืนยัน]** ว่าต้องการสำหรับ paid pilot หรือไม่

## 2. Use case/user story พร้อม acceptance criteria

| ID | User story | Acceptance criteria |
|---|---|---|
| US-01 | ในฐานะ operator ฉันโหลดไฟล์สองฝั่งและเห็น field ก่อนตรวจ | `/api/inspect` คืน fields + metadata + SHA-256; format ไม่รองรับ → 400 พร้อมข้อความ |
| US-02 | ในฐานะ operator ฉันเลือก key ของแต่ละฝั่ง | ปุ่มรันเปิดเมื่อมีไฟล์และ key ครบ; key ว่างใน record ถูกรายงานเป็น `invalid_key` ไม่ถูกทิ้งเงียบ |
| US-03 | ในฐานะ operator ฉันได้ mapping ที่แนะนำและแก้ได้ | mapping แนะนำมี confidence; header ไทยที่ต่างกันไม่ถูก map ผิดด้วย confidence 1.0 |
| US-04 | ในฐานะ operator ฉันเลือก normalization สำหรับข้อมูลลูกค้าไทย | `thai_customer` ทำให้ชื่อ/เบอร์ (+66, เลขไทย)/เลขภาษี/วันที่ พ.ศ./ที่อยู่ เทียบได้ แต่ evidence แสดงค่าต้นฉบับ; profile ที่ไม่รู้จัก → error |
| US-05 | ในฐานะ operator ฉันเห็นผลแยกตามสถานะ | summary นับ 6 สถานะ, match rate ไม่แสดง 100% ถ้ามี exception; key ซ้ำเป็น `duplicate` |
| US-06 | ในฐานะ operator ฉันเปิด evidence ราย record | เห็นค่าสองฝั่ง field ที่ต่าง และเหตุผลของ rule |
| US-07 | ในฐานะ operator ฉันเห็นคู่ที่น่าจะเป็น record เดียวกัน | fuzzy candidate แสดงคะแนน/เหตุผล, ปรับ threshold/limit/ปิดได้, ไม่ auto-approve |
| US-08 | ในฐานะ operator ฉันตัดสิน exception | mark `approved`/`rejected`/`needs-review`; rerun ยังคงสถานะ; summary นับสถานะ review |
| US-09 | ในฐานะ operator ฉันส่งหลักฐานให้ลูกค้า | ดาวน์โหลด Markdown report และ audit package JSON; คัดลอก SQL |
| US-10 | ในฐานะ agency ฉันส่ง export ที่ปิดข้อมูลส่วนบุคคล | redacted export ปิด field ที่ตรง profile โดยไม่แก้ผลต้นฉบับ |
| US-11 | ในฐานะผู้ประเมิน ฉันลองด้วยข้อมูลตัวอย่าง | ปุ่ม `ใช้ข้อมูลตัวอย่าง` โหลด sample จาก package ได้ทั้ง editable และ wheel install |
| US-12 | ในฐานะ operator ฉันรันซ้ำแล้วได้ผลเดิม | input + configuration เดิม → fingerprint และผลเดิม |

## 3. Functional requirements

| FR | ข้อกำหนด | Priority | Phase | สถานะ |
|---|---|---|---|---|
| FR-01 | อ่าน CSV/TSV/XLSX/Parquet เป็น canonical dataset `mvw.input.v1` | Must | V1.1 P0 | Implemented + tested |
| FR-02 | input SHA-256 และ configuration fingerprint (ไม่ขึ้นกับลำดับ) | Must | V1.1 P0 | Implemented + tested |
| FR-03 | `/api/inspect` คืน fields/metadata โดยไม่ reconcile | Must | V1.1 | Implemented + tested (API) |
| FR-04 | เลือก key; key ว่าง → `invalid_key` | Must | V1 | Implemented + tested |
| FR-05 | heuristic mapping พร้อม confidence และจำนวนจำกัด | Must | V1 | Implemented + tested |
| FR-06 | normalization `generic` / `thai_customer` โดยไม่แก้ raw evidence | Should | V1.1 P1 | Implemented + tested |
| FR-07 | reconcile 6 สถานะพร้อม reason | Must | V1 | Implemented + tested |
| FR-08 | fuzzy candidate แบบ advisory มีขอบเขต ปิดได้ symmetric | Should | V1.1 P1 | Implemented + tested |
| FR-09 | review status ต่อ evidence + summary + ตรวจ id/status ที่ไม่รู้จัก | Should | V1.1 P1 | Implemented + tested |
| FR-10 | audit package `mvw.audit.v1` ไม่มีค่า raw และเสถียร | Should | V1.1 P1 | Implemented + tested |
| FR-11 | Markdown report ดาวน์โหลดได้ | Must | V1 | Implemented (web) ไม่มี test |
| FR-12 | SQL ตรวจซ้ำแบบ read-only, quote column, table strict | Should | V1 | Implemented + tested |
| FR-13 | redacted export ตาม field profile | Must | V1.1 P0 | Implemented + tested |
| FR-14 | จำกัด body 20 MB, 200,000 แถว, 500 คอลัมน์ → 413 | Must | V1.1 | Implemented + tested |
| FR-15 | bind loopback เว้นแต่ `--allow-remote` | Must | V1.1 | Implemented + tested (pytest) |
| FR-16 | sample data สังเคราะห์ใน package + route `/fixtures` ป้องกัน traversal | Should | V1.1 | Implemented + tested |
| FR-17 | profiling ไม่เปิดเผยค่า (DuckDB + fallback) นับ key ซ้ำ | Could | V1.1 | Implemented + tested |
| FR-18 | `/api/normalization-profiles` และ `/api/health` | Must | V1.1 | Implemented + tested |
| FR-19 | profile templates customer/invoice/transaction/product | Could | P2 | Not started (MVW-122) |
| FR-20 | connector-level Excel/Parquet adapters | Could | P2 | Not started (MVW-121) |

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| BA (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `apps/api/src/migration_validation_api/server.py`, `apps/api/src/migration_validation_api/cli.py`
- `packages/reconciliation-core/src/reconciliation_core/*.py`, `connectors/file-input/src/migration_input/input_contract.py`
- `packages/audit/`, `packages/privacy/`, `packages/data-engine/`
- `evals/tests/*.py`, `apps/web/app/page.tsx`
- `(solo-empire) plans/decision-context/MIGRATION-VALIDATION-WORKBENCH-V1.1.md`
