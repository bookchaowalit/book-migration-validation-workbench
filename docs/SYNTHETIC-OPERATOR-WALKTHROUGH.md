# คู่มือทดลองตรวจ migration ด้วยข้อมูลไทยสมมติ

สถานะ: **AI-assisted synthetic dry run** เตรียมเมื่อ 2026-10-15
ยังไม่มีหลักฐานว่าผู้ใช้ที่ไม่ได้สร้างระบบทำ walkthrough สำเร็จ
ไม่ใช่ผลทดลองผู้ใช้ 5 คน ผลลดเวลา 50% หรือการส่งข้อเสนอ paid pilot

เป้าหมายคือให้ operator อธิบายได้ว่าความต่างใดเป็นเพียงรูปแบบเบอร์โทร
และความต่างใดยังต้องให้คนตรวจ โดยไม่อนุมัติการแก้ข้อมูลต้นทาง

## เตรียมเครื่อง

ใช้ Python 3.10+ สำหรับสคริปต์ด้านล่าง ไม่ต้องติดตั้ง dependency
ไม่ต้องใช้ credentials, บัญชีผู้ให้บริการ หรือเชื่อมฐานข้อมูล
รันจาก root ของ repository นี้:

```bash
PYTHONPATH=packages/reconciliation-core/src:packages/privacy/src python3 evals/operator_walkthrough.py
```

สคริปต์อ่านเฉพาะไฟล์ที่ commit อยู่ใน
`apps/api/src/migration_validation_api/sample_data/`:

- `thai_customers_legacy.csv`: ระบบเก่าสมมติ 2 แถว
- `thai_customers_target.csv`: ระบบใหม่สมมติ 2 แถว

ไม่รับ path จากภายนอก ไม่ส่ง HTTP ไม่เขียนไฟล์ และไม่แก้ CSV
ผลพิมพ์มี SHA-256 ของ input กับ summary แต่ไม่มีค่าแต่ละ record
ต้องได้ `result: passed` และ `human_operator_completion: false`
สคริปต์ทดสอบ pure core/การปกปิด ไม่ครอบคลุม browser, HTTP หรือการดาวน์โหลด

## Operator ทดลองผ่านหน้าจอ

เตรียม API และ web ตามหัวข้อเริ่มใช้งานใน [README](../README.md)
ขั้นนี้ต้องติดตั้ง dependencies ที่ README ระบุ; เปิด API เฉพาะ loopback
ใช้ไฟล์สมมติที่ระบุด้านบนเท่านั้น ไม่ใช้ข้อมูลลูกค้าจริง
ปุ่ม “ใช้ข้อมูลตัวอย่าง” ใช้ fixture อีกชุด จึงให้อัปโหลดสองไฟล์นี้เอง

1. เปิด `http://localhost:3000` แล้วเลือกไฟล์ legacy/target ในช่องระบบเก่า/ระบบใหม่
2. เลือก key ทั้งสองฝั่งเป็น `account_no` ตรวจ mapping ให้จับคู่ชื่อเดียวกันทั้ง
   `account_no`, `customer_name`, `phone`, `status`
3. เลือก `Generic — conservative text` แล้วรันการตรวจ ควรพบ 2 records,
   matched 0, value mismatch 2 เปิด TH-001 แล้วชี้ให้เห็นว่าเบอร์โทรมีขีดเพิ่ม
4. เปลี่ยนเป็น `Thai customer` แล้วรันใหม่ ควรพบ matched 1, exceptions 1,
   match rate 50% โดย TH-001 ตรงกันหลัง normalization
   **50% นี้คือสัดส่วน record ที่ตรงกัน ไม่ใช่การลดเวลาทำงาน**
5. เปิด TH-001 ตรวจว่าหลักฐาน raw ยังแสดงเบอร์สองรูปแบบเดิม
   เปิด TH-002 ตรวจชื่อ `สุดา ตัวอย่าง` เทียบกับ `สุดา ตัวอย่างใหม่`
   การเปลี่ยนชื่อยังเป็น value mismatch ไม่ควรสรุปว่าถูกต้องโดยอัตโนมัติ
6. เลือก TH-002 แล้วกด `Needs review` และรันด้วย configuration เดิมอีกครั้ง
   ตรวจว่าสถานะ review ของแถวนี้ยังอยู่ โดยผลตรวจความต่างไม่หาย
7. ดาวน์โหลด report และ audit package ตรวจว่า report มี summary,
   profile, fingerprints และสถานะ review; audit มี row references
   และ fingerprints โดยไม่มี raw record values อย่านำไฟล์ไปเผยแพร่ก่อนตรวจ
   การ review อยู่ในหน่วยความจำของหน้าจอ ไม่ใช่การบันทึกถาวรข้าม refresh
8. จบโดยปิด server และลบไฟล์ดาวน์โหลดสมมติที่ไม่ต้องการเก็บ

ถ้าตัวเลขต่าง ให้ตรวจ key, mapping, profile และชื่อไฟล์ก่อน
หยุดและบันทึกขั้นตอนที่ติดขัด ห้ามแก้ expected result เพียงเพื่อให้ผ่าน
ข้อผิดพลาดติดตั้ง/HTTP/browser ให้บันทึกแยกจากผล pure core

## บันทึกการทดลองของผู้ที่ไม่ได้สร้างระบบ

ให้ operator เติมหลังลองจริงเท่านั้น ผู้สร้างหรือ AI ไม่เติมแทน:

```text
วันที่/เวลาและ timezone:
commit ที่ใช้:
ผู้ทดลอง: alias ที่ยินยอมให้บันทึก (ไม่ต้องระบุข้อมูลส่วนตัว)
ไม่ได้เป็นผู้สร้างส่วนที่ทดสอบ: ใช่/ไม่ใช่
เครื่อง/เวอร์ชัน Python/Node:
ขั้นที่ทำได้ด้วยตนเอง:
ขั้นที่ต้องมีคนช่วยและคำแนะนำที่ได้รับ:
ผล Generic / Thai customer ที่เห็นจริง:
อธิบายความต่าง TH-001 กับ TH-002 ด้วยคำของตนเอง:
สถานะ Needs review หลัง rerun:
ตรวจ report / audit แล้วหรือไม่:
ปัญหาและเวลาที่พบ (ถ้ามี):
สรุปสำเร็จ/ยังไม่สำเร็จ พร้อมเหตุผล:
```

จะถือ human acceptance สำเร็จเมื่อมีบันทึกลงวันที่จากผู้ทดลองที่ไม่ได้สร้าง
ทำขั้นตอนสำคัญได้และอธิบายผลได้จริง โดยเปิดเผยความช่วยเหลือที่ได้รับ
ยังต้องทำ operator trial, baseline time comparison และ paid pilot แยกต่างหาก

## บันทึกการตรวจที่มีอยู่

2026-10-15: AI-assisted dry run ของสคริปต์ pure core ผ่านด้วย fixture ไทยสองไฟล์
ตรวจ Generic mismatch 2 → Thai match 1/mismatch 1, เก็บ raw evidence,
จำลอง Needs review และ rerun, ปกปิด key/name/phone ใน evidence สำเร็จ
ไม่ได้ทดลอง browser/HTTP ในรอบนี้ และ **ยังรอ non-builder operator completion**
ผลสคริปต์นี้ใช้ยืนยันความทำซ้ำได้ของข้อมูลสมมติ ไม่ใช้แทนบันทึกคนทดลอง
