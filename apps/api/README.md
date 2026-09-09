# API boundary — FastAPI

เจ้าของ HTTP transport และ request orchestration ของ workbench ใช้ FastAPI + Pydantic

- รับ `/api/inspect`, `/api/normalization-profiles` และ `/api/reconcile`
- `/api/reconcile` รองรับ `fuzzy_enabled`, `fuzzy_threshold` และ `fuzzy_candidate_limit`; ผลลัพธ์จะบอก configuration และบังคับ `auto_approval: false`
- ตรวจ request size และรูปแบบข้อมูล พร้อม OpenAPI schema
- เรียก file-input adapter, reconciliation core และ privacy package
- เรียก data-engine adapter เพื่อทำ profiling ที่ไม่เปิดเผยค่า raw
- สร้าง `audit_package` ที่มี input/config fingerprints, rule version, summary และ row references โดยไม่ใส่ raw values
- ไม่เก็บ request payload, credentials หรือข้อมูลลูกค้าลง disk

รันด้วย Uvicorn แบบ local-only; business logic ยังแยกอยู่ใน package ที่ไม่ผูกกับ web framework

```bash
python3 -m pip install -e .
python3 run.py
```

เอกสาร API: `http://127.0.0.1:8765/docs`
