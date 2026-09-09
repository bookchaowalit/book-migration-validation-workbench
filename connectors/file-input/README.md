# File input connectors

แปลง CSV, TSV, XLSX และ Parquet (เมื่อมี PyArrow) ให้เป็น canonical dataset contract เดียวกัน

boundary นี้คำนวณ fingerprint จาก bytes จริง แต่ไม่เขียน raw input ลง disk และไม่ส่งข้อมูลไปบริการภายนอก

