# ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ

นายเมทนี พูลสมบัติ 6821500060 · รายวิชา Object-Oriented Programming

โครงร่างครบตาม [`docs/backlog.md`](docs/backlog.md) — สถาปัตยกรรม 3 ชั้น `domain/` (กติกาธุรกิจ ไม่ผูกฐานข้อมูล) → `repository/` (คุยกับ MariaDB) → `api/` (FastAPI + Jinja2 + HTMX + Pico.css)

## โครงสร้างโปรเจกต์

```
domain/       กติกาธุรกิจทั้งหมด (Person, Case, Appointment, Schedule, LawFirm, CaseAssignment, errors)
repository/   Repository class ต่อตาราง (User/Client/Case/Appointment/Assignment) คุยกับ MariaDB ตรงๆ ไม่ใช้ ORM
api/          web layer — main.py เป็น app factory บางๆ, deps.py ของใช้ร่วม, routes/ แยกตามพื้นที่งาน, auth.py ล็อกอิน/session/require_role
templates/    Jinja2 templates (Pico.css + HTMX ผ่าน CDN)
static/       theme.css — โทเค็นสี/คลาสของระบบ
db/           schema.sql (โครงตาราง MariaDB 6 ตาราง), seed.sql (ข้อมูลตัวอย่าง), migrations/
docs/         backlog/proposal/uml/index/pitch/survey (เอกสาร) + diagrams/
tools/        generate_seed.py — สร้าง db/seed.sql (อยู่นอกระบบที่ส่งมอบ)
tests/        pytest — ส่วนใหญ่ไม่ต้องต่อฐานข้อมูล ยกเว้น test_repository.py
Dockerfile, docker-compose.yml   รันทั้งเว็บ + MariaDB + phpMyAdmin ด้วย Docker (ทางเลือกแทน XAMPP)
```

## ติดตั้ง

ต้องมี Python 3.10 ขึ้นไป (พัฒนาและทดสอบบน 3.12) และ XAMPP ที่เปิด MariaDB ไว้แล้ว

```bash
# 1) สร้างและเปิดใช้งาน virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2) ติดตั้ง dependencies
pip install -r requirements.txt
```

## ตั้งค่าฐานข้อมูล (MariaDB ผ่าน XAMPP + phpMyAdmin)

1. เปิด XAMPP Control Panel แล้ว Start โมดูล MySQL/MariaDB
2. เปิด phpMyAdmin (`http://localhost/phpmyadmin`) → แท็บ **Databases** → สร้างฐานข้อมูลชื่อ `lawfirm-db` collation `utf8mb4_unicode_ci`
3. เลือกฐานข้อมูล `lawfirm-db` ที่เพิ่งสร้าง → แท็บ **Import** → เลือกไฟล์ [`db/schema.sql`](db/schema.sql) → กด Go (ได้ตารางครบ 6 ตาราง)
4. แท็บ **Import** อีกครั้ง → เลือกไฟล์ [`db/seed.sql`](db/seed.sql) → กด Go (ได้ข้อมูลตัวอย่างครบ)

ค่าเชื่อมต่อดีฟอลต์ (`repository/db.py`)คือ `root` รหัสผ่านว่าง ฐาน `lawfirm-db` ที่ `localhost:3306` — ตรงกับค่าเริ่มต้นของ XAMPP พอดี **ไม่ต้องตั้งค่าอะไรเพิ่ม** ถ้าเครื่องที่รันใช้ค่าเริ่มต้นของ XAMPP อยู่แล้ว

ถ้าต้อง override (เช่น มีรหัสผ่าน root หรือใช้พอร์ตอื่น) ให้ตั้งผ่าน `.env`:

```bash
cp .env.example .env
# แก้ DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME / SECRET_KEY ตามจริง
```

### สร้าง seed.sql ใหม่ (ไม่บังคับ)

`db/seed.sql` ในโปรเจกต์นี้สร้างไว้แล้ว แต่ถ้าต้องการสร้างใหม่ (เช่น อยากได้ข้อมูลที่นัดคร่อม "วันนี้" ของวันที่รันจริง):

```bash
python tools/generate_seed.py     # เขียนทับ db/seed.sql
```

จากนั้นนำเข้าไฟล์ใหม่ผ่าน phpMyAdmin ตามขั้นตอนด้านบนอีกครั้ง (ต้อง **เคลียร์ข้อมูลเดิมในตารางทั้ง 6 ก่อน** ไม่งั้นจะชนกับ `UNIQUE`/`AUTO_INCREMENT` เดิม — ใน phpMyAdmin ใช้แท็บ **Operations** ของแต่ละตาราง → Empty the table (TRUNCATE) เรียงจาก `appointment_changes` → `appointments` → `case_assignments` → `cases` → `clients` → `users`)

## รันเซิร์ฟเวอร์

```bash
uvicorn api.main:app --reload
```

เปิดเบราว์เซอร์ที่ `http://127.0.0.1:8000/` → เจอหน้าล็อกอิน

## รันด้วย Docker (ทางเลือกแทน XAMPP)

รันทั้งเว็บ (FastAPI + uvicorn), ฐานข้อมูล (MariaDB 10.4) และ phpMyAdmin พร้อมกันด้วยคำสั่งเดียว โดยไม่ต้องติดตั้ง Python/MariaDB/XAMPP บนเครื่องเลย — ต้องมีแค่ [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**ต้องปิด XAMPP ก่อน** (หรือแก้พอร์ตในไฟล์ `docker-compose.yml`) เพราะทั้งคู่แย่งพอร์ต 3306 กัน

```bash
docker compose up --build
```

- เว็บแอป: `http://localhost:8000`
- phpMyAdmin: `http://localhost:8080` (เซิร์ฟเวอร์ = `db`, user `root`, รหัสผ่านว่าง)

ครั้งแรกที่รัน container ของ `db` จะสร้างฐานข้อมูล `lawfirm-db` และนำเข้า `db/schema.sql` + `db/seed.sql` ให้อัตโนมัติ (ผ่าน `docker-entrypoint-initdb.d`) ไม่ต้องทำตามขั้นตอน phpMyAdmin manual ด้านบนอีก

หยุดการทำงาน: กด `Ctrl+C` แล้วรัน `docker compose down` (ข้อมูลใน MariaDB จะยังอยู่ในเครื่องผ่าน Docker volume ครั้งหน้ารันใหม่ไม่ต้อง seed ซ้ำ)

ถ้าแก้ `db/schema.sql`/`db/seed.sql` แล้วอยากให้ import ใหม่ทั้งหมด (init script รันแค่ตอน volume ว่างเปล่าเท่านั้น) ให้ลบข้อมูลเดิมก่อน:

```bash
docker compose down -v   # ลบ volume ของ db ด้วย — ข้อมูลทั้งหมดในนั้นหายถาวร
docker compose up --build
```

โค้ดในโปรเจกต์ถูก mount เข้า container ของ `web` โดยตรง (`--reload` เปิดอยู่) แก้ไฟล์แล้วเว็บ reload เองเหมือนรันแบบ local ปกติ ไม่ต้อง build ใหม่ทุกครั้ง (build ใหม่เฉพาะตอนแก้ `requirements.txt`)

## บัญชีตัวอย่างสำหรับตรวจงาน

รหัสผ่านเดียวกันทุกบัญชี: **`password123`**

| บทบาท | ชื่อผู้ใช้ |
|---|---|
| admin | `admin` |
| manager | `manager1` |
| lawyer | `lawyer1` ถึง `lawyer8` |

ล็อกอินด้วย `lawyer1` แล้วเห็น sidebar ซ้าย (BL-34) พร้อมแถวเมนู "คดีรอตอบรับ" ที่มี badge ตัวเลขเสมอ (BL-36 — กดเปิด popup รับ/ไม่รับคดี ไม่บังปฏิทินอีกต่อไป) และปฏิทินเดือนขึ้นบนสุดทันที (BL-32) — คลิกนัดในปฏิทินเปิด popup ข้อมูลคดี (เลขคดี/สถานะ/คู่ความ/ศาล) พร้อมปุ่มลงนัดถัดไป ถัดมาเป็นตารางวันนี้แบบการ์ด (มีนัดของวันที่เปิดใช้งานจริงเสมอ เพราะ seed อิงจากวันที่รันสคริปต์) และแผง "ใกล้ครบกำหนด" ทางขวา (BL-35) · ล็อกอินด้วย `manager1` เห็นคดีที่ยังไม่มีทนายตอบรับ + ภาระงานทนาย + ปุ่ม "เพิ่มคดีใหม่" (`/manager/cases/new`, BL-31) เลือกลูกความเดิมหรือเพิ่มลูกความใหม่ในฟอร์มเดียวกันได้ · ล็อกอินด้วย `admin` เห็นหน้าจัดการผู้ใช้ · ทุกหน้าเป็นโทนสีม่วง/ลาเวนเดอร์ + การ์ด/chip ตาม `mockup/dashboard.html` แล้ว (BL-33 ถึง BL-36, `static/theme.css`) — ย่อหน้าต่างแคบกว่ามือถือแล้ว sidebar สลับกลับเป็นแถบบนอัตโนมัติ

## รัน Unit Test

```bash
pytest
```

เทสส่วนใหญ่ (`domain/` ทั้งหมด) **ไม่ต้องต่อฐานข้อมูล** ยกเว้น `tests/test_repository.py` และ `tests/test_auth.py`'s DB-dependent cases ที่ต่อ `lawfirm-db` จริงผ่าน XAMPP

**ข้อควรระวัง** — `tests/test_repository.py` จะ **TRUNCATE ทั้ง 6 ตารางก่อนรันทุกครั้ง** เพื่อทดสอบแบบสะอาด หลังรัน `pytest` แล้วข้อมูลตัวอย่างจะหายไป ถ้าจะกลับไปเปิดเว็บดูข้อมูลต่อ ให้นำเข้า `db/seed.sql` ใหม่ผ่าน phpMyAdmin ตามขั้นตอนด้านบนอีกครั้ง

## หมายเหตุสำหรับผู้สอน/ผู้เรียน

- `domain/` ไม่ import อะไรจาก `repository/` เลย (ทิศทางเดียว) — ทดสอบได้ทั้งหมดโดยไม่ต้องต่อฐานข้อมูลตามที่ backlog กำหนด
- รหัสผ่านเก็บด้วย `hashlib.scrypt` ของ stdlib พร้อม salt ต่อผู้ใช้ ไม่ใช้ library เข้ารหัสเพิ่ม
- session เป็น signed cookie (ผ่าน `itsdangerous`) ไม่เก็บ state ฝั่งเซิร์ฟเวอร์
- ทุก route ตรวจสิทธิ์ผ่าน `require_role()` จุดเดียว (`api/auth.py`) ไม่มี `if role ==` กระจายอยู่ในโค้ด route
- วันที่แสดงผลเป็น พ.ศ. ผ่าน Jinja2 filter `|thaidate` (`api/deps.py`) แต่เก็บและนับวันเตือน (3/1/15 วัน) เป็น ค.ศ. เสมอ ตามที่ตัดสินไว้
