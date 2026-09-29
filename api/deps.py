"""ของที่ใช้ร่วมกันหลาย router — Jinja filters/globals, DB dependency, ตัวช่วยภาระงาน

ย้ายมาตรงๆ จาก api/main.py (BL-32/34/35/36) ไม่เปลี่ยนพฤติกรรม:
- `templates` + filter/global ทั้งหมดลงทะเบียนตอน import โมดูลนี้ (api/main.py import ที่นี่ก่อน include router)
- `get_db` คือ FastAPI dependency ตัวเดียวที่เปิด/ปิด connection แทน get_connection()+close เองในแต่ละ handler
"""

import os
from datetime import date, timedelta

from fastapi import Request
from fastapi.templating import Jinja2Templates

from api.auth import SESSION_COOKIE, read_session_cookie
from domain.appointment import ClientMeeting, CourtHearing, FilingDeadline
from domain.assignment import WITHDRAW_REASONS
from domain.case import CaseStatus
from domain.person import Lawyer, Manager, SystemUser
from repository.appointment_repo import AppointmentRepository
from repository.assignment_repo import AssignmentRepository
from repository.case_repo import CaseRepository
from repository.user_repo import UserRepository
from repository.db import get_connection

templates = Jinja2Templates(directory="templates")


def thaidate(value, fmt: str = "date") -> str:
    """แสดงผลเป็น พ.ศ. — เก็บ/นับวันเตือน (3/1/15) เป็น ค.ศ. เสมอ ใช้ filter นี้เฉพาะตอนแสดงผลเท่านั้น"""
    if value is None:
        return "-"
    buddhist_year = value.year + 543
    if fmt == "datetime":
        return f"{value.day:02d}/{value.month:02d}/{buddhist_year} {value.hour:02d}:{value.minute:02d}"
    return f"{value.day:02d}/{value.month:02d}/{buddhist_year}"


templates.env.filters["thaidate"] = thaidate

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]
templates.env.filters["thai_month"] = lambda month: THAI_MONTHS[month - 1]

CASE_STATUS_LABELS_TH = {
    CaseStatus.OPEN: "เปิดคดี", CaseStatus.FILED: "ยื่นฟ้อง", CaseStatus.TRIAL: "สืบพยาน",
    CaseStatus.JUDGED: "ตัดสิน", CaseStatus.FINAL: "ถึงที่สุด", CaseStatus.CLOSED: "ปิดคดี",
    CaseStatus.CANCELLED: "ยกเลิก",
}


def case_status_th(status: CaseStatus) -> str:
    return CASE_STATUS_LABELS_TH.get(status, status.value)


templates.env.filters["case_status_th"] = case_status_th


def days_until(value: date) -> int:
    """สำหรับ badge นับถอยหลังในรายการเตือน (BL-35) — ไม่กระทบการนับวันเตือนจริงใน domain/"""
    return (value - date.today()).days


templates.env.filters["days_until"] = days_until


def get_db():
    """เปิด connection หนึ่งตัวต่อหนึ่ง request ปิดให้เอง — handler รับผ่าน Depends(get_db) แล้วไม่ต้อง close เอง"""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def sidebar_user(request: Request) -> SystemUser | None:
    """Jinja global — sidebar ใน layout.html รู้บทบาทเองจาก cookie โดยไม่ต้องส่ง current_user จากทุก route (BL-34)"""
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_session_cookie(token) if token else None
    if user_id is None:
        return None
    conn = get_connection()
    try:
        return UserRepository(conn).get_by_id(user_id)
    finally:
        conn.close()


templates.env.globals["sidebar_user"] = sidebar_user


def css_version() -> int:
    """ต่อท้าย /static/theme.css?v=... — แก้ CSS แล้วเบราว์เซอร์โหลดไฟล์ใหม่ทันที ไม่ค้างแคชเก่า"""
    return int(os.path.getmtime("static/theme.css"))


templates.env.globals["css_version"] = css_version


def _workload_for(conn, lawyer: Lawyer) -> int:
    """คดีที่ตอบรับอยู่ + นัดในอีก 30 วัน — Lawyer.workload() (BL-23)"""
    accepted_cases = CaseRepository(conn).list_accepted_by_lawyer(lawyer.id)
    today = date.today()
    horizon = today + timedelta(days=30)
    upcoming = [
        a for a in AppointmentRepository(conn).list_by_lawyer(lawyer.id)
        if today <= a.starts_at.date() <= horizon
    ]
    return lawyer.workload(cases=accepted_cases, appointments=upcoming)


def _lawyer_workloads(conn) -> list[tuple[Lawyer, int]]:
    lawyers = UserRepository(conn).list_by_role("lawyer")
    return sorted(((lw, _workload_for(conn, lw)) for lw in lawyers), key=lambda pair: pair[1])


def lawyer_pending(user: SystemUser | None) -> list:
    """Jinja global — badge+popup คดีรอตอบรับใน sidebar ต้องมีข้อมูลนี้ทุกหน้า ไม่ใช่แค่ /schedule/today (BL-36)"""
    if not isinstance(user, Lawyer):
        return []
    conn = get_connection()
    try:
        return AssignmentRepository(conn).list_pending_for_lawyer(user.id)
    finally:
        conn.close()


templates.env.globals["lawyer_pending"] = lawyer_pending


def lawyer_workload(user: SystemUser | None) -> int:
    """Jinja global — ตัวเลขภาระงานใน dialog ยืนยันรับคดี (ทุกหน้าที่มี sidebar)"""
    if not isinstance(user, Lawyer):
        return 0
    conn = get_connection()
    try:
        return _workload_for(conn, user)
    finally:
        conn.close()


templates.env.globals["lawyer_workload"] = lawyer_workload


def withdraw_request_count(user: SystemUser | None) -> int:
    """Jinja global — badge "คำขอถอนตัว" ใน sidebar ของ manager"""
    if not isinstance(user, Manager):
        return 0
    conn = get_connection()
    try:
        return len(AssignmentRepository(conn).list_withdraw_requests())
    finally:
        conn.close()


templates.env.globals["withdraw_request_count"] = withdraw_request_count
templates.env.globals["WITHDRAW_REASONS"] = WITHDRAW_REASONS
