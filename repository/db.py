"""เชื่อมต่อ MariaDB 10.4 ของ XAMPP ด้วย mysql-connector-python — BL-18

ค่า default ตรงกับที่ตัดสินใน backlog.md หัวข้อ 2 (6 ก.ย. 2569):
root, รหัสผ่านว่าง, ฐานข้อมูลชื่อ lawfirm-db (สร้างไว้ใน phpMyAdmin แล้ว) —
clone แล้วรันได้ทันทีโดยไม่ต้องตั้งค่า · override ได้ผ่าน .env (ไม่ commit)
"""

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "lawfirm-db"),
    )
