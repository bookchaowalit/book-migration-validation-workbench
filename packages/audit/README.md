# Audit package

`migration_audit` สร้าง JSON artifact ที่ deterministic สำหรับเก็บเป็นหลักฐาน
ของ migration validation run

สิ่งที่ package เก็บไว้:

- input metadata และ SHA-256 ของไฟล์ทั้งสองฝั่ง
- configuration fingerprint, key, table และ applied mapping
- normalization/fuzzy rule configuration และ `rule_version`
- summary, review summary และ evidence ที่อ้าง `evidence_id` กับเลขแถว

สิ่งที่ package ไม่เก็บ:

- raw source rows
- raw keys
- mismatch values
- fuzzy candidate keys

จึงใช้เป็น artifact สำหรับ audit หรือส่งต่อให้ผู้ review ได้โดยไม่ export
ข้อมูล record ออกจากระบบโดยไม่ตั้งใจ
