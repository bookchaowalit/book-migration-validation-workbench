# Deployment boundary

ยังเป็น local-only prototype จึงยังไม่มี production deployment, authentication, persistent storage หรือ cloud credentials

จุดที่ต้องเพิ่มก่อน pilot production:

- container/process definition
- environment and secret contract
- access control and retention policy
- rollback, monitoring และ backup/replay

