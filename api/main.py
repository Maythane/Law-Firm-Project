"""App factory แบบบาง — สร้าง FastAPI, เสิร์ฟ static, include router ตามพื้นที่งาน

route ทั้งหมดย้ายไป api/routes/ (auth, dashboard, manager, admin, schedule, cases, reminders)
ของใช้ร่วม (Jinja filters/globals, get_db) อยู่ api/deps.py
URL/HTML/DB schema เหมือนเดิมทุกอย่าง ดูขอบเขตงานเต็มที่ backlog.md#bl-20..bl-40
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import api.deps  # noqa: F401 — ลงทะเบียน Jinja filters/globals บน templates ตอน import
from api.routes import admin, auth, cases, dashboard, manager, reminders, schedule

app = FastAPI(title="ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(manager.router)
app.include_router(admin.router)
app.include_router(schedule.router)
app.include_router(cases.router)
app.include_router(reminders.router)
