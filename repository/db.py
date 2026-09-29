"""เชื่อมต่อ MariaDB 10.4 ของ XAMPP ด้วย mysql-connector-python — BL-18

ค่า default ตรงกับที่ตัดสินใน backlog.md หัวข้อ 2 (6 ก.ย. 2569):
root, รหัสผ่านว่าง, ฐานข้อมูลชื่อ lawfirm-db (สร้างไว้ใน phpMyAdmin แล้ว) —
clone แล้วรันได้ทันทีโดยไม่ต้องตั้งค่า · override ได้ผ่าน .env (ไม่ commit)
"""

import os
import re
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def _conn_kwargs(database: str | None = None) -> dict:
    kwargs = dict(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
    )
    if database is not None:
        kwargs["database"] = database
    return kwargs


def get_connection():
    return mysql.connector.connect(**_conn_kwargs(os.environ.get("DB_NAME", "lawfirm-db")))


# ฐานสำหรับเทสแยกจากฐานแอปเสมอ — เทส TRUNCATE ทุกตาราง ห้ามโดน lawfirm-db (ดู guard ใน tests/test_repository.py)
TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "lawfirm_test")


def is_test_db_allowed(test_db: str, app_db: str) -> bool:
    """ฐานเทสต้องไม่ชนฐานแอป (DB_NAME) และต้องไม่ใช่ lawfirm-db เด็ดขาด — คืน False แปลว่าห้าม TRUNCATE"""
    return test_db != app_db and test_db != "lawfirm-db"

_TEST_TABLES = {
    "users", "clients", "cases", "case_assignments",
    "appointments", "case_notes", "case_events", "appointment_changes",
}
_test_db_ready = False


def get_test_connection():
    """connection สำหรับเทสเท่านั้น — เปิดฐาน TEST_DB_NAME (สร้าง + ลง schema ให้ถ้ายังไม่มี) ไม่แตะฐานของแอป"""
    _ensure_test_database()
    return mysql.connector.connect(**_conn_kwargs(TEST_DB_NAME))


def _ensure_test_database() -> None:
    """สร้างฐานเทส + โหลด db/schema.sql เมื่อตารางยังไม่ครบ — รันครั้งเดียวต่อโปรเซส pytest"""
    global _test_db_ready
    if _test_db_ready:
        return
    if not re.fullmatch(r"[A-Za-z0-9_-]+", TEST_DB_NAME):
        raise ValueError(f"TEST_DB_NAME ไม่ปลอดภัย: {TEST_DB_NAME!r}")
    admin = mysql.connector.connect(**_conn_kwargs())
    cur = admin.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{TEST_DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    admin.close()
    check = mysql.connector.connect(**_conn_kwargs(TEST_DB_NAME))
    cur = check.cursor()
    cur.execute("SHOW TABLES")
    have = {row[0] for row in cur.fetchall()}
    if not _TEST_TABLES <= have:
        schema = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
        statements = "".join(
            line for line in schema.read_text(encoding="utf-8").splitlines(keepends=True)
            if not line.lstrip().startswith("--")
        ).split(";")
        for stmt in statements:
            if stmt.strip():
                cur.execute(stmt)
        check.commit()
    check.close()
    _test_db_ready = True
