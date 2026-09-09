# Reconciliation core

Deterministic business logic สำหรับเทียบข้อมูลสอง dataset

รับ canonical fields/rows และคืน summary, mapping suggestions, status และ evidence ราย record โดยไม่รู้เรื่อง HTTP, browser, database หรือ provider ภายนอก

Normalization profile อยู่ใน `normalization.py` และใช้เฉพาะค่าที่นำมาเปรียบเทียบ:

- `generic` — Unicode normalization, case folding และ collapse whitespace
- `thai_customer` — เพิ่มกฎ conservative สำหรับชื่อ, เบอร์โทร, เลขภาษี, วันที่ และที่อยู่

ค่าต้นฉบับใน evidence ไม่ถูก mutate และ profile ที่ใช้จะถูกบันทึกในผลลัพธ์เพื่อให้ rerun ได้

Fuzzy matching อยู่ใน `fuzzy.py` และเป็น advisory เท่านั้น:

- ให้คะแนนจาก mapped fields ที่ normalize แล้ว และจำกัดจำนวน candidate กับขนาด dataset
- แสดง candidate ได้ทั้งฝั่งที่ไม่มี target และฝั่งที่ไม่มี legacy
- `review_threshold` ปรับได้ แต่ candidate ไม่เคยถูก auto-approve หรือเปลี่ยนเป็น `match`
