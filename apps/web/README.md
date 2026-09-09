# Web boundary — Next.js

Browser UI ของ Migration Validation Workbench

ใช้ Next.js App Router + TypeScript สำหรับ dashboard และ upload/review flow โดย UI เรียก FastAPI ของ `apps/api` และไม่ฝัง credential ใด ๆ

กำหนด API ปลายทางผ่าน `NEXT_PUBLIC_API_BASE_URL` ซึ่ง default เป็น `http://127.0.0.1:8765`

```bash
npm install
npm run dev
```

เปิด `http://localhost:3000`
