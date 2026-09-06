# ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ

นายเมทนี พูลสมบัติ 6821500060 · รายวิชา Object-Oriented Programming

โครงร่างครบตาม [`backlog.md`](backlog.md) — สถาปัตยกรรม 3 ชั้น `domain/` (กติกาธุรกิจ ไม่ผูกฐานข้อมูล) → `repository/` (คุยกับ MariaDB) → `api/` (FastAPI + Jinja2 + HTMX + Pico.css)

## โครงสร้างโปรเจกต์

```
domain/       กติกาธุรกิจทั้งหมด (Person, Case, Appointment, Schedule, LawFirm, CaseAssignment, errors)
repository/   คุยกับ MariaDB ด้วย mysql-connector-python ตรงๆ ไม่ใช้ ORM
api/          FastAPI app, routes, auth (login/session/require_role)
templates/    Jinja2 templates (Pico.css + HTMX ผ่าน CDN)
tools/        generate_seed.py — สร้าง seed.sql (อยู่นอกระบบที่ส่งมอบ)
tests/        pytest — ส่วนใหญ่ไม่ต้องต่อฐานข้อมูล ยกเว้น test_repository.py
schema.sql    โครงตาราง MariaDB (6 ตาราง)
seed.sql      ข้อมูลตัวอย่าง (สร้างจาก tools/generate_seed.py)
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
3. เลือกฐานข้อมูล `lawfirm-db` ที่เพิ่งสร้าง → แท็บ **Import** → เลือกไฟล์ [`schema.sql`](schema.sql) → กด Go (ได้ตารางครบ 6 ตาราง)
4. แท็บ **Import** อีกครั้ง → เลือกไฟล์ [`seed.sql`](seed.sql) → กด Go (ได้ข้อมูลตัวอย่างครบ)

ค่าเชื่อมต่อดีฟอลต์ (`repository/db.py`)คือ `root` รหัสผ่านว่าง ฐาน `lawfirm-db` ที่ `localhost:3306` — ตรงกับค่าเริ่มต้นของ XAMPP พอดี **ไม่ต้องตั้งค่าอะไรเพิ่ม** ถ้าเครื่องที่รันใช้ค่าเริ่มต้นของ XAMPP อยู่แล้ว

ถ้าต้อง override (เช่น มีรหัสผ่าน root หรือใช้พอร์ตอื่น) ให้ตั้งผ่าน `.env`:

```bash
cp .env.example .env
# แก้ DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME / SECRET_KEY ตามจริง
```

### สร้าง seed.sql ใหม่ (ไม่บังคับ)

`seed.sql` ในโปรเจกต์นี้สร้างไว้แล้ว แต่ถ้าต้องการสร้างใหม่ (เช่น อยากได้ข้อมูลที่นัดคร่อม "วันนี้" ของวันที่รันจริง):

```bash
python tools/generate_seed.py     # เขียนทับ seed.sql ที่ root ของโปรเจกต์
```

จากนั้นนำเข้าไฟล์ใหม่ผ่าน phpMyAdmin ตามขั้นตอนด้านบนอีกครั้ง (ต้อง **เคลียร์ข้อมูลเดิมในตารางทั้ง 6 ก่อน** ไม่งั้นจะชนกับ `UNIQUE`/`AUTO_INCREMENT` เดิม — ใน phpMyAdmin ใช้แท็บ **Operations** ของแต่ละตาราง → Empty the table (TRUNCATE) เรียงจาก `appointment_changes` → `appointments` → `case_assignments` → `cases` → `clients` → `users`)

## รันเซิร์ฟเวอร์

```bash
uvicorn api.main:app --reload
```

เปิดเบราว์เซอร์ที่ `http://127.0.0.1:8000/` → เจอหน้าล็อกอิน

## บัญชีตัวอย่างสำหรับตรวจงาน

รหัสผ่านเดียวกันทุกบัญชี: **`password123`**

| บทบาท | ชื่อผู้ใช้ |
|---|---|
| admin | `admin` |
| manager | `manager1` |
| lawyer | `lawyer1` ถึง `lawyer8` |

ล็อกอินด้วย `lawyer1` แล้วเห็นตารางวันนี้ทันที (มีนัดของวันที่เปิดใช้งานจริงเสมอ เพราะ seed อิงจากวันที่รันสคริปต์) · ล็อกอินด้วย `manager1` เห็นคดีที่ยังไม่มีทนายตอบรับ + ภาระงานทนาย · ล็อกอินด้วย `admin` เห็นหน้าจัดการผู้ใช้

## รัน Unit Test

```bash
pytest
```

เทสส่วนใหญ่ (`domain/` ทั้งหมด) **ไม่ต้องต่อฐานข้อมูล** ยกเว้น `tests/test_repository.py` และ `tests/test_auth.py`'s DB-dependent cases ที่ต่อ `lawfirm-db` จริงผ่าน XAMPP

**ข้อควรระวัง** — `tests/test_repository.py` จะ **TRUNCATE ทั้ง 6 ตารางก่อนรันทุกครั้ง** เพื่อทดสอบแบบสะอาด หลังรัน `pytest` แล้วข้อมูลตัวอย่างจะหายไป ถ้าจะกลับไปเปิดเว็บดูข้อมูลต่อ ให้นำเข้า `seed.sql` ใหม่ผ่าน phpMyAdmin ตามขั้นตอนด้านบนอีกครั้ง

## หมายเหตุสำหรับผู้สอน/ผู้เรียน

- `domain/` ไม่ import อะไรจาก `repository/` เลย (ทิศทางเดียว) — ทดสอบได้ทั้งหมดโดยไม่ต้องต่อฐานข้อมูลตามที่ backlog กำหนด
- รหัสผ่านเก็บด้วย `hashlib.scrypt` ของ stdlib พร้อม salt ต่อผู้ใช้ ไม่ใช้ library เข้ารหัสเพิ่ม
- session เป็น signed cookie (ผ่าน `itsdangerous`) ไม่เก็บ state ฝั่งเซิร์ฟเวอร์
- ทุก route ตรวจสิทธิ์ผ่าน `require_role()` จุดเดียว (`api/auth.py`) ไม่มี `if role ==` กระจายอยู่ในโค้ด route
- วันที่แสดงผลเป็น พ.ศ. ผ่าน Jinja2 filter `|thaidate` (`api/main.py`) แต่เก็บและนับวันเตือน (3/1/15 วัน) เป็น ค.ศ. เสมอ ตามที่ตัดสินไว้
