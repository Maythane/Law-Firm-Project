"""BL-20: FastAPI + Jinja2 + Pico.css/HTMX — หน้าแรกคือตารางวันนี้
BL-21: หน้าคดี + หน้าเตือน — ตรวจสิทธิ์ผ่าน user.can_view_case() จุดเดียว (BR-15)
BL-25: ล็อกอิน + session (signed cookie) + require_role() — ทุก route ที่รู้ตัวตนผ่าน dependency นี้จุดเดียว
BL-26: หน้ามอบหมายของ manager + ตารางภาระงานทนาย
BL-27: กล่องคดีรอการตอบรับบน dashboard ทนาย — อัปเดตด้วย HTMX เฉพาะกล่องนั้น
BL-28: ปฏิทินรายเดือนของทนาย — จิ้มวันแล้วไปหน้าตารางวันนั้น
BL-29: หน้าจัดการผู้ใช้ของ admin — เพิ่ม/ปิดใช้งาน/รีเซ็ตรหัสผ่าน (ลบไม่ได้ เพราะมีนัด/การมอบหมายอ้างอิงอยู่)
BL-31: หน้า "เพิ่มคดีใหม่" ของ manager — เปิดคดีก่อนยื่นฟ้อง (ก่อนมีเลขคดีดำ) เลือกลูกความเดิมหรือเพิ่มลูกความใหม่ในฟอร์มเดียวกันได้
BL-33: theme สีม่วง/ลาเวนเดอร์ตาม mockup — override ตัวแปรสีของ Pico.css ผ่าน static/theme.css ไม่แก้โครง template
BL-34: sidebar ซ้ายแทน nav บนสุด (responsive แบบ hybrid CSS — จอแคบสลับกลับเป็นแถบบนแบบเดิม)
BL-35: แปลงรายการ/ตารางเป็นการ์ดตาม mockup + แผง "ใกล้ครบกำหนด" บน /schedule/today
BL-36: คดีรอตอบรับย้ายจากแถบบนสุดไปเป็น badge+popup ใน sidebar (ทุกหน้า) — HTMX out-of-band swap ตัวแรกของโปรเจกต์
BL-40: หน้า "คดีของฉัน" ของทนาย + จัดการคดีในหน้าคดี (นัด/สถานะ/เลขคดี/โน้ต/ขอถอนตัว) + manager อนุมัติถอนตัวแล้วมอบหมายคนใหม่
ดูขอบเขตงานเต็มที่ backlog.md#bl-20, #bl-21, #bl-25, #bl-26, #bl-27, #bl-28, #bl-29, #bl-31, #bl-33, #bl-34, #bl-35, #bl-36, #bl-40
"""

import calendar
import os
from dataclasses import replace
from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from urllib.parse import quote

import mysql.connector
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.auth import (
    SESSION_COOKIE, authenticate, create_session_cookie, hash_password, read_session_cookie,
    require_role, verify_password,
)
from domain.appointment import ClientMeeting, CourtHearing, FilingDeadline
from domain.assignment import WITHDRAW_REASONS
from domain.case import Case, CaseNote, CaseStatus
from domain.errors import AssignmentError, InvalidStatusTransition, ScheduleConflictError
from domain.firm import LawFirm
from domain.person import Admin, Client, Lawyer, Manager, SystemUser
from domain.schedule import Schedule
from repository import appointment_repo, assignment_repo, case_repo, client_repo, user_repo
from repository.db import get_connection

WORKLOAD_OVERLOAD_THRESHOLD = 15  # ponytail: เกณฑ์ตายตัวเลือกเอง (ดูจากการกระจายจริงใน seed.sql: 10-28) ไม่มีสเปกกำหนดตัวเลข ปรับได้ทีหลังถ้าต้องแม่นกว่านี้

app = FastAPI(title="ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ")
app.mount("/static", StaticFiles(directory="static"), name="static")
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


def sidebar_user(request: Request) -> SystemUser | None:
    """Jinja global — sidebar ใน layout.html รู้บทบาทเองจาก cookie โดยไม่ต้องส่ง current_user จากทุก route (BL-34)"""
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_session_cookie(token) if token else None
    if user_id is None:
        return None
    conn = get_connection()
    user = user_repo.get_by_id(conn, user_id)
    conn.close()
    return user


templates.env.globals["sidebar_user"] = sidebar_user


def css_version() -> int:
    """ต่อท้าย /static/theme.css?v=... — แก้ CSS แล้วเบราว์เซอร์โหลดไฟล์ใหม่ทันที ไม่ค้างแคชเก่า"""
    return int(os.path.getmtime("static/theme.css"))


templates.env.globals["css_version"] = css_version


def lawyer_pending(user: SystemUser | None) -> list:
    """Jinja global — badge+popup คดีรอตอบรับใน sidebar ต้องมีข้อมูลนี้ทุกหน้า ไม่ใช่แค่ /schedule/today (BL-36)"""
    if not isinstance(user, Lawyer):
        return []
    conn = get_connection()
    pending = assignment_repo.list_pending_for_lawyer(conn, user.id)
    conn.close()
    return pending


templates.env.globals["lawyer_pending"] = lawyer_pending


def lawyer_workload(user: SystemUser | None) -> int:
    """Jinja global — ตัวเลขภาระงานใน dialog ยืนยันรับคดี (ทุกหน้าที่มี sidebar)"""
    if not isinstance(user, Lawyer):
        return 0
    conn = get_connection()
    workload = _workload_for(conn, user)
    conn.close()
    return workload


templates.env.globals["lawyer_workload"] = lawyer_workload


def withdraw_request_count(user: SystemUser | None) -> int:
    """Jinja global — badge "คำขอถอนตัว" ใน sidebar ของ manager"""
    if not isinstance(user, Manager):
        return 0
    conn = get_connection()
    count = len(assignment_repo.list_withdraw_requests(conn))
    conn.close()
    return count


templates.env.globals["withdraw_request_count"] = withdraw_request_count
templates.env.globals["WITHDRAW_REASONS"] = WITHDRAW_REASONS


def _month_neighbors(year: int, month: int) -> tuple[int, int, int, int]:
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return prev_year, prev_month, next_year, next_month

@app.get("/style-guide", response_class=HTMLResponse)
def style_guide(request: Request):
    """หน้าอ้างอิงโทเค็นสี/spacing/component สด — ไม่ใช่ฟีเจอร์ของระบบ อยู่นอกขอบเขต backlog เหมือน tools/generate_seed.py"""
    return templates.TemplateResponse("style_guide.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": error})


@app.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    user = authenticate(username, password)
    if user is None:
        return RedirectResponse("/login?error=1", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(SESSION_COOKIE, create_session_cookie(user.id), httponly=True)
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")


@app.get("/dashboard")
def dashboard(current_user: SystemUser = Depends(require_role())):
    if isinstance(current_user, Lawyer):
        return RedirectResponse("/schedule/today")
    if isinstance(current_user, Manager):
        return RedirectResponse("/manager/dashboard")
    return RedirectResponse("/admin/dashboard")


def _workload_for(conn, lawyer: Lawyer) -> int:
    """คดีที่ตอบรับอยู่ + นัดในอีก 30 วัน — Lawyer.workload() (BL-23)"""
    accepted_cases = case_repo.list_accepted_by_lawyer(conn, lawyer.id)
    today = date.today()
    horizon = today + timedelta(days=30)
    upcoming = [
        a for a in appointment_repo.list_by_lawyer(conn, lawyer.id)
        if today <= a.starts_at.date() <= horizon
    ]
    return lawyer.workload(cases=accepted_cases, appointments=upcoming)


def _lawyer_workloads(conn) -> list[tuple[Lawyer, int]]:
    lawyers = user_repo.list_by_role(conn, "lawyer")
    return sorted(((lw, _workload_for(conn, lw)) for lw in lawyers), key=lambda pair: pair[1])


@app.get("/manager/dashboard", response_class=HTMLResponse)
def manager_dashboard(request: Request, manager: Manager = Depends(require_role(Manager))):
    conn = get_connection()
    unassigned_cases = case_repo.list_without_accepted_lawyer(conn)
    waiting = assignment_repo.list_pending_for_cases(conn, unassigned_cases)
    declined = assignment_repo.list_unresolved_declined(conn)
    withdraw_requests = assignment_repo.list_withdraw_requests(conn)
    workloads = _lawyer_workloads(conn)
    conn.close()
    return templates.TemplateResponse(
        "dashboard/manager.html",
        {
            "request": request, "manager": manager, "unassigned_cases": unassigned_cases,
            "waiting": waiting, "declined": declined, "workloads": workloads, "withdraw_requests": withdraw_requests,
        },
    )


_PROGRESS_STEPS = [
    CaseStatus.OPEN, CaseStatus.FILED, CaseStatus.TRIAL, CaseStatus.JUDGED, CaseStatus.FINAL, CaseStatus.CLOSED,
]


def _progress(case: Case) -> dict | None:
    """ขั้นความคืบหน้าของคดี (1-6) สำหรับแถบ progress — คดียกเลิกไม่มีแถบ (คืน None)"""
    if case.status not in _PROGRESS_STEPS:
        return None
    step = _PROGRESS_STEPS.index(case.status) + 1
    return {"step": step, "total": len(_PROGRESS_STEPS), "pct": round(step / len(_PROGRESS_STEPS) * 100)}


@app.get("/manager/lawyers/{lawyer_id}", response_class=HTMLResponse)
def lawyer_cases(
    request: Request, lawyer_id: int, manager: Manager = Depends(require_role(Manager)), tab: str = "active",
):
    """คดีที่ทนายคนหนึ่งดูแลอยู่ + ความคืบหน้า — manager ดูอย่างเดียว (แก้/มอบหมายทำที่หน้าเดิม)"""
    conn = get_connection()
    lawyer = user_repo.get_by_id(conn, lawyer_id)
    if not isinstance(lawyer, Lawyer):
        conn.close()
        raise HTTPException(404, "ไม่พบทนาย")
    assignments = assignment_repo.list_accepted_for_lawyer(conn, lawyer.id)
    workload = _workload_for(conn, lawyer)
    appointments = appointment_repo.list_by_lawyer(conn, lawyer.id)
    latest = case_repo.latest_event_by_case(conn, [a.case.id for a in assignments])
    conn.close()

    now = datetime.now()
    next_appt = {}
    for a in sorted(appointments, key=lambda a: a.starts_at):
        if not a.is_done and a.starts_at >= now:
            next_appt.setdefault(a.case.id, a)

    finished = (CaseStatus.CLOSED, CaseStatus.CANCELLED)
    status_counts = {}
    for a in assignments:
        status_counts[a.case.status] = status_counts.get(a.case.status, 0) + 1
    rows = [
        {
            "assignment": a, "case": a.case, "next": next_appt.get(a.case.id), "progress": _progress(a.case),
            # ยังไม่มีเหตุการณ์ใดในคดี: ใช้วันที่ทนายตอบรับแทน
            "updated": latest.get(a.case.id) or ("ตอบรับคดี", a.responded_at),
        }
        for a in assignments
        if (a.case.status in finished) == (tab == "closed")
    ]
    rows.sort(key=lambda r: (r["next"] is None, r["next"].starts_at if r["next"] else now, r["case"].title))
    return templates.TemplateResponse(
        "manager/lawyer_cases.html",
        {
            "request": request, "lawyer": lawyer, "lawyer_load": workload, "rows": rows, "tab": tab,
            # ไม่ใช้ชื่อ "workload" — layout.html ตั้งตัวแปรชื่อนี้ทับ (ภาระงานของผู้ล็อกอิน) ทำให้เลขในหน้านี้เป็น 0
            "status_counts": [(s, status_counts[s]) for s in CaseStatus if s in status_counts],
            "total": len(assignments),
        },
    )


@app.get("/manager/cases/new", response_class=HTMLResponse)
def new_case_form(request: Request, manager: Manager = Depends(require_role(Manager))):
    conn = get_connection()
    clients = client_repo.list_all(conn)
    conn.close()
    return templates.TemplateResponse(
        "manager/new_case.html",
        {
            "request": request, "manager": manager, "clients": clients, "error": None,
            "values": {}, "today": date.today().isoformat(),
        },
    )


@app.post("/manager/cases/new", response_class=HTMLResponse)
def create_case(
    request: Request,
    manager: Manager = Depends(require_role(Manager)),
    client_id: str = Form(""),
    new_client_name: str = Form(""),
    new_client_citizen_id: str = Form(""),
    new_client_phone: str = Form(""),
    new_client_company: str = Form(""),
    title: str = Form(...),
    client_role: str = Form(...),
    opposing_party: str = Form(...),
    court_name: str = Form(...),
    opened_date: str = Form(...),
):
    """BL-31: เลือกลูกความเดิม (client_id) หรือเพิ่มลูกความใหม่ (new_client_name ไม่ว่าง) — เลือกได้ทางใดทางหนึ่ง"""
    conn = get_connection()

    if new_client_name.strip():
        client = client_repo.add(
            conn,
            Client(
                name=new_client_name, citizen_id=new_client_citizen_id,
                phone=new_client_phone, company=new_client_company or None,
            ),
        )
    elif client_id:
        client = client_repo.get_by_id(conn, int(client_id))
    else:
        client = None

    if client is None:
        clients = client_repo.list_all(conn)
        conn.close()
        return templates.TemplateResponse(
            "manager/new_case.html",
            {
                "request": request, "manager": manager, "clients": clients,
                "error": "ต้องเลือกลูกความเดิม หรือกรอกอย่างน้อยชื่อลูกความใหม่",
                "values": {
                    "title": title, "client_role": client_role, "opposing_party": opposing_party,
                    "court_name": court_name, "opened_date": opened_date,
                    "new_client_name": new_client_name, "new_client_citizen_id": new_client_citizen_id,
                    "new_client_phone": new_client_phone, "new_client_company": new_client_company,
                },
                "today": date.today().isoformat(),
            },
        )

    case = case_repo.add(
        conn,
        Case(
            title=title, client=client, client_role=client_role,
            opposing_party=opposing_party, court_name=court_name,
            opened_date=date.fromisoformat(opened_date),
        ),
    )
    conn.close()
    return RedirectResponse(f"/cases/{case.id}", status_code=303)


def _notify_back(back: str) -> str:
    """กล่องแจ้งเตือนที่ dashboard manager จะเปิดค้างไว้หลังจัดการเสร็จ — รับเฉพาะสองค่านี้ (ค่าอื่นใช้ unassigned)"""
    return back if back in ("declined", "unassigned") else "unassigned"


@app.get("/manager/cases/{case_id}/assign", response_class=HTMLResponse)
def assign_form(
    request: Request, case_id: int, manager: Manager = Depends(require_role(Manager)), back: str = "",
):
    conn = get_connection()
    case = case_repo.get_by_id(conn, case_id)
    if case is None:
        conn.close()
        raise HTTPException(404, "ไม่พบคดี")
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    workloads = _lawyer_workloads(conn)
    conn.close()
    return templates.TemplateResponse(
        "manager/assign.html",
        {
            "request": request, "case": case, "workloads": workloads,
            "threshold": WORKLOAD_OVERLOAD_THRESHOLD, "error": None, "warning": None,
            "back": _notify_back(back),
        },
    )


@app.post("/manager/cases/{case_id}/assign", response_class=HTMLResponse)
def assign_submit(
    request: Request,
    case_id: int,
    manager: Manager = Depends(require_role(Manager)),
    lawyer_id: int = Form(...),
    is_lead: bool = Form(False),
    confirm_overload: str = Form(""),
    back: str = Form(""),
):
    back = _notify_back(back)
    conn = get_connection()
    case = case_repo.get_by_id(conn, case_id)
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    lawyer = user_repo.get_by_id(conn, lawyer_id)
    workload = _workload_for(conn, lawyer)

    if workload >= WORKLOAD_OVERLOAD_THRESHOLD and confirm_overload != "true":
        workloads = _lawyer_workloads(conn)
        conn.close()
        return templates.TemplateResponse(
            "manager/assign.html",
            {
                "request": request, "case": case, "workloads": workloads,
                "threshold": WORKLOAD_OVERLOAD_THRESHOLD, "error": None,
                "warning": (
                    f"{lawyer.display_name()} มีภาระงาน {workload} รายการ "
                    f"(เกินเกณฑ์ {WORKLOAD_OVERLOAD_THRESHOLD}) ยืนยันจะมอบหมายต่อไหม?"
                ),
                "pending_lawyer_id": lawyer_id, "pending_is_lead": is_lead, "back": back,
            },
        )

    firm = LawFirm()  # ไม่ได้ใช้ firm.cases เลย แค่ยืม assign_lawyer() ที่บังคับ BR-17 มาใช้
    try:
        assignment = firm.assign_lawyer(case, lawyer, assigned_by=manager, is_lead=is_lead)
    except AssignmentError as e:
        workloads = _lawyer_workloads(conn)
        conn.close()
        return templates.TemplateResponse(
            "manager/assign.html",
            {
                "request": request, "case": case, "workloads": workloads,
                "threshold": WORKLOAD_OVERLOAD_THRESHOLD, "error": str(e), "warning": None, "back": back,
            },
        )
    assignment_repo.add(conn, assignment)
    conn.close()
    return RedirectResponse(f"/manager/dashboard#notify-{back}", status_code=303)


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, admin: Admin = Depends(require_role(Admin))):
    """BL-39: สถิติผู้ใช้ 3 บทบาท แยกเปิด/ปิดใช้งาน — สำนักเดียว ไม่มีสถิติคดี (อยู่ที่ manager dashboard แทน)"""
    conn = get_connection()
    counts = user_repo.count_by_role(conn)
    conn.close()
    return templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "admin": admin, "counts": counts},
    )


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, admin: Admin = Depends(require_role(Admin)), error: str | None = None):
    conn = get_connection()
    users = user_repo.list_all(conn)
    conn.close()
    return templates.TemplateResponse(
        "admin/users.html", {"request": request, "admin": admin, "users": users, "error": error},
    )


@app.get("/admin/users/new", response_class=HTMLResponse)
def admin_new_user_form(request: Request, admin: Admin = Depends(require_role(Admin))):
    return templates.TemplateResponse(
        "admin/users_new.html", {"request": request, "admin": admin, "error": None, "values": {}},
    )


@app.post("/admin/users/new", response_class=HTMLResponse)
def admin_create_user(
    request: Request,
    admin: Admin = Depends(require_role(Admin)),
    name: str = Form(...),
    citizen_id: str = Form(...),
    phone: str = Form(""),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    license_no: str = Form(""),
):
    conn = get_connection()
    if user_repo.find_by_username(conn, username) is not None:
        conn.close()
        return templates.TemplateResponse(
            "admin/users_new.html",
            {
                "request": request, "admin": admin, "error": f'ชื่อผู้ใช้ "{username}" มีอยู่แล้ว',
                "values": {
                    "name": name, "citizen_id": citizen_id, "phone": phone, "username": username,
                    "role": role, "license_no": license_no,
                },
            },
        )

    password_hash = hash_password(password)
    common = dict(name=name, citizen_id=citizen_id, phone=phone, username=username, password_hash=password_hash)
    if role == "lawyer":
        new_user = Lawyer(**common, license_no=license_no)
    elif role == "manager":
        new_user = Manager(**common)
    else:
        new_user = Admin(**common)
    user_repo.add(conn, new_user)
    conn.close()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/toggle-active")
def admin_toggle_active(user_id: int, admin: Admin = Depends(require_role(Admin))):
    conn = get_connection()
    user = user_repo.get_by_id(conn, user_id)
    if user is None:
        conn.close()
        raise HTTPException(404, "ไม่พบผู้ใช้")
    user_repo.set_active(conn, user_id, not user.is_active)
    conn.close()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/edit", response_class=HTMLResponse)
def admin_edit_user(
    request: Request,
    user_id: int,
    admin: Admin = Depends(require_role(Admin)),
    name: str = Form(...),
    username: str = Form(...),
    new_password: str = Form(""),
):
    """BL-37: แก้ชื่อที่ใช้แสดง/username/รหัสผ่าน (เว้นว่าง = ไม่เปลี่ยน) — รวมกับรีเซ็ตรหัสผ่านเดิมเป็นฟอร์มเดียว ไม่แก้ role"""
    conn = get_connection()
    existing = user_repo.find_by_username(conn, username)
    if existing is not None and existing.id != user_id:
        conn.close()
        return admin_users(request, admin, error=f'ชื่อผู้ใช้ "{username}" มีอยู่แล้ว')
    password_hash = hash_password(new_password) if new_password.strip() else None
    user_repo.update_profile(conn, user_id, name, username, password_hash)
    conn.close()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/account/edit")
def account_edit(
    request: Request,
    current_user: SystemUser = Depends(require_role()),
    name: str = Form(...),
    username: str = Form(...),
    current_password: str = Form(""),
    new_password: str = Form(""),
):
    """BL-38: self-service แก้ไขบัญชีตัวเอง (ทุกบทบาท) จากกล่องใน sidebar
    บังคับรหัสผ่านเดิมเฉพาะตอนเปลี่ยนรหัสผ่านใหม่จริง — แก้แค่ชื่อ/username ไม่ต้องยืนยันรหัสเดิม
    ฟอร์มฝังอยู่ใน layout.html ทุกหน้า เลยไม่มีหน้าเดียวให้ re-render ตอน error — ส่งกลับไปหน้าเดิม (referer) พร้อม query param แทน (แบบเดียวกับ /login?error=1)
    """
    back = request.headers.get("referer") or "/dashboard"
    sep = "&" if "?" in back else "?"
    conn = get_connection()
    password_hash = None
    if new_password.strip():
        if not verify_password(current_password, current_user.password_hash):
            conn.close()
            return RedirectResponse(f"{back}{sep}account_error=รหัสผ่านเดิมไม่ถูกต้อง", status_code=303)
        password_hash = hash_password(new_password)
    existing = user_repo.find_by_username(conn, username)
    if existing is not None and existing.id != current_user.id:
        conn.close()
        return RedirectResponse(f"{back}{sep}account_error=ชื่อผู้ใช้นี้มีอยู่แล้ว", status_code=303)
    user_repo.update_profile(conn, current_user.id, name, username, password_hash)
    conn.close()
    return RedirectResponse(back, status_code=303)


@app.get("/schedule/today", response_class=HTMLResponse)
def schedule_today(
    request: Request,
    lawyer: Lawyer = Depends(require_role(Lawyer)),
    year: int | None = None,
    month: int | None = None,
):
    """BL-32: ปฏิทินเดือนขึ้นบนสุด — คลิกแต่ละนัดเปิด popup ข้อมูลคดี ไม่ใช่ navigate เหมือน /schedule/month"""
    today = date.today()
    cal_year = year or today.year
    cal_month = month or today.month
    conn = get_connection()
    schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, lawyer.id))
    pending = assignment_repo.list_pending_for_lawyer(conn, lawyer.id)
    conn.close()
    appointments = schedule.day_view(lawyer, today)
    reminders = schedule.upcoming_reminders(lawyer, today)[:3]

    days_by_number = {d.day: appts for d, appts in schedule.month_view(lawyer, cal_year, cal_month).items()}
    calendar_weeks = []
    for week in calendar.monthcalendar(cal_year, cal_month):
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(None)
            else:
                appts = days_by_number.get(day_num, [])
                row.append({"day": day_num, "shown": appts[:2], "more": max(0, len(appts) - 2)})
        calendar_weeks.append(row)
    prev_year, prev_month, next_year, next_month = _month_neighbors(cal_year, cal_month)

    return templates.TemplateResponse(
        "schedule/today.html",
        {
            "request": request, "lawyer": lawyer, "appointments": appointments, "today": today,
            "pending": pending, "year": cal_year, "month": cal_month, "calendar_weeks": calendar_weeks,
            "prev_year": prev_year, "prev_month": prev_month,
            "next_year": next_year, "next_month": next_month, "reminders": reminders,
        },
    )


@app.get("/schedule/day", response_class=HTMLResponse)
def schedule_day(request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)), d: str | None = None):
    target_day = date.fromisoformat(d) if d else date.today()
    conn = get_connection()
    schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, lawyer.id))
    conn.close()
    appointments = schedule.day_view(lawyer, target_day)
    return templates.TemplateResponse(
        "schedule/day.html",
        {"request": request, "lawyer": lawyer, "appointments": appointments, "day": target_day},
    )


@app.get("/schedule/month", response_class=HTMLResponse)
def schedule_month(
    request: Request,
    lawyer: Lawyer = Depends(require_role(Lawyer)),
    year: int | None = None,
    month: int | None = None,
):
    today = date.today()
    year = year or today.year
    month = month or today.month
    conn = get_connection()
    schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, lawyer.id))
    conn.close()
    days_by_number = {d.day: appts for d, appts in schedule.month_view(lawyer, year, month).items()}

    calendar_weeks = []
    for week in calendar.monthcalendar(year, month):
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(None)
            else:
                appts = days_by_number.get(day_num, [])
                row.append({
                    "day": day_num,
                    "count": len(appts),
                    "kinds": sorted({a.kind_label() for a in appts}),
                })
        calendar_weeks.append(row)

    prev_year, prev_month, next_year, next_month = _month_neighbors(year, month)
    return templates.TemplateResponse(
        "schedule/month.html",
        {
            "request": request, "lawyer": lawyer, "year": year, "month": month, "today": today,
            "calendar_weeks": calendar_weeks,
            "prev_year": prev_year, "prev_month": prev_month,
            "next_year": next_year, "next_month": next_month,
        },
    )


@app.post("/assignments/{assignment_id}/accept", response_class=HTMLResponse)
def accept_assignment(request: Request, assignment_id: int, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or assignment.lawyer.id != lawyer.id:
        conn.close()
        raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
    try:
        assignment.accept()
    except AssignmentError as e:
        conn.close()
        raise HTTPException(409, str(e))
    assignment_repo.update_status(conn, assignment)
    pending = assignment_repo.list_pending_for_lawyer(conn, lawyer.id)
    workload = _workload_for(conn, lawyer)
    conn.close()
    return templates.TemplateResponse(
        "schedule/_pending_swap_response.html", {"request": request, "pending": pending, "workload": workload}
    )


@app.post("/assignments/{assignment_id}/decline", response_class=HTMLResponse)
def decline_assignment(
    request: Request,
    assignment_id: int,
    reason: str = Form(...),
    lawyer: Lawyer = Depends(require_role(Lawyer)),
):
    conn = get_connection()
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or assignment.lawyer.id != lawyer.id:
        conn.close()
        raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
    try:
        assignment.decline(reason)
    except ValueError as e:
        pending = assignment_repo.list_pending_for_lawyer(conn, lawyer.id)
        workload = _workload_for(conn, lawyer)
        conn.close()
        return templates.TemplateResponse(
            "schedule/_pending_swap_response.html",
            {
                "request": request, "pending": pending, "workload": workload,
                "decline_error": str(e), "error_assignment_id": assignment_id,
            },
        )
    assignment_repo.update_status(conn, assignment)
    pending = assignment_repo.list_pending_for_lawyer(conn, lawyer.id)
    workload = _workload_for(conn, lawyer)
    conn.close()
    return templates.TemplateResponse(
        "schedule/_pending_swap_response.html", {"request": request, "pending": pending, "workload": workload}
    )


@app.get("/schedule/new", response_class=HTMLResponse)
def new_appointment_form(
    request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)), case_id: int | None = None,
):
    """case_id เลือกล่วงหน้าได้ผ่าน query — ปุ่ม "ลงนัดถัดไป" จาก popup ปฏิทิน (BL-32)"""
    conn = get_connection()
    cases = case_repo.list_accepted_by_lawyer(conn, lawyer.id)
    conn.close()
    return templates.TemplateResponse(
        "schedule/form.html",
        {
            "request": request, "lawyer": lawyer, "cases": cases, "error": None,
            "values": {"case_id": case_id} if case_id else {},
        },
    )


def _build_appointment(kind, case, lawyer, starts_at, ends_at, location, court_name, room_no, triggered_by_event):
    if kind == "hearing":
        return CourtHearing(
            case=case, lawyer=lawyer, starts_at=starts_at, ends_at=ends_at,
            location=location, court_name=court_name or "", room_no=room_no or "",
        )
    if kind == "meeting":
        return ClientMeeting(case=case, lawyer=lawyer, starts_at=starts_at, ends_at=ends_at, location=location)
    return FilingDeadline(
        case=case, lawyer=lawyer, starts_at=starts_at, ends_at=ends_at,
        location=location, triggered_by_event=triggered_by_event or "",
    )


@app.post("/schedule/new", response_class=HTMLResponse)
def create_appointment(
    request: Request,
    lawyer: Lawyer = Depends(require_role(Lawyer)),
    case_id: int = Form(...),
    kind: str = Form(...),
    starts_at: str = Form(...),
    ends_at: str = Form(...),
    location: str = Form(""),
    court_name: str = Form(""),
    room_no: str = Form(""),
    triggered_by_event: str = Form(""),
):
    conn = get_connection()
    case = case_repo.get_by_id(conn, case_id)
    case._assignments.extend(assignment_repo.list_for_case(conn, case))

    appt = _build_appointment(
        kind, case, lawyer,
        datetime.fromisoformat(starts_at), datetime.fromisoformat(ends_at),
        location, court_name, room_no, triggered_by_event,
    )
    schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, lawyer.id))
    try:
        schedule.add(appt)
    except (ScheduleConflictError, AssignmentError) as e:
        cases = case_repo.list_accepted_by_lawyer(conn, lawyer.id)
        conn.close()
        return templates.TemplateResponse(
            "schedule/form.html",
            {
                "request": request, "lawyer": lawyer, "cases": cases, "error": str(e),
                "values": {
                    "case_id": case_id, "kind": kind, "starts_at": starts_at, "ends_at": ends_at,
                    "location": location, "court_name": court_name, "room_no": room_no,
                    "triggered_by_event": triggered_by_event,
                },
            },
        )
    appointment_repo.add(conn, appt)
    conn.close()
    return RedirectResponse("/schedule/today", status_code=303)


def _load_case(conn, case_id: int):
    case = case_repo.get_by_id(conn, case_id)
    if case is None:
        conn.close()
        raise HTTPException(404, "ไม่พบคดี")
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    return case


def _load_case_for(conn, case_id: int, user: SystemUser):
    """โหลดคดี + ตรวจสิทธิ์จุดเดียว (BR-15) — ทุก route ที่แตะคดีผ่านฟังก์ชันนี้"""
    case = _load_case(conn, case_id)
    if not user.can_view_case(case):
        conn.close()
        raise HTTPException(403, "ไม่มีสิทธิ์เข้าถึงคดีนี้")
    return case


def _back_to_case(case_id: int, error: str | None = None) -> RedirectResponse:
    url = f"/cases/{case_id}" + (f"?error={quote(error)}" if error else "")
    return RedirectResponse(url, status_code=303)


def _open_appointments(appointments) -> list:
    """นัดที่ยังไม่ถึง/ยังไม่เสร็จ/ยังไม่ยกเลิก — ใช้ตรวจ BR-9 ตอนปิดคดี"""
    now = datetime.now()
    return [a for a in appointments if not a.is_cancelled and not a.is_done and a.starts_at >= now]


@app.get("/cases", response_class=HTMLResponse)
def my_cases(
    request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)),
    tab: str = "active", q: str = "", status: str = "",
):
    """หน้า "คดีของฉัน" — คดีที่ตอบรับแล้ว แยกแท็บกำลังดำเนินการ / ปิดแล้ว-ยกเลิก เรียงตามนัดถัดไป"""
    conn = get_connection()
    assignments = assignment_repo.list_accepted_for_lawyer(conn, lawyer.id)
    appointments = appointment_repo.list_by_lawyer(conn, lawyer.id)
    conn.close()

    now = datetime.now()
    next_appt = {}
    for a in sorted(appointments, key=lambda a: a.starts_at):
        if not a.is_done and a.starts_at >= now:
            next_appt.setdefault(a.case.id, a)

    finished = (CaseStatus.CLOSED, CaseStatus.CANCELLED)
    rows = [
        {"assignment": a, "case": a.case, "next": next_appt.get(a.case.id)}
        for a in assignments
        if (a.case.status in finished) == (tab == "closed")
    ]
    needle = q.strip().lower()
    if needle:
        rows = [
            r for r in rows
            if any(
                needle in (text or "").lower()
                for text in (
                    r["case"].title, r["case"].black_case_no, r["case"].red_case_no,
                    r["case"].client.display_name(), r["case"].client.name, r["case"].opposing_party,
                )
            )
        ]
    if status:
        rows = [r for r in rows if r["case"].status.value == status]
    rows.sort(key=lambda r: (r["next"] is None, r["next"].starts_at if r["next"] else now, r["case"].title))
    return templates.TemplateResponse(
        "cases/list.html",
        {
            "request": request, "rows": rows, "tab": tab, "q": q, "status": status,
            "statuses": [
                s for s in CaseStatus if (s in finished) == (tab == "closed")
            ],
        },
    )


@app.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: int, current_user: SystemUser = Depends(require_role())):
    conn = get_connection()
    case = _load_case_for(conn, case_id, current_user)
    appointments = sorted(appointment_repo.list_by_case(conn, case_id), key=lambda a: a.starts_at)
    notes = case_repo.list_notes(conn, case_id)
    events = case_repo.list_events(conn, case_id)
    conn.close()
    my_assignment = next(
        (a for a in case._assignments if a.lawyer.id == current_user.id and a.status.value == "accepted"), None
    )
    next_status = case.next_status()
    return templates.TemplateResponse(
        "cases/detail.html",
        {
            "request": request, "case": case, "appointments": appointments, "user": current_user,
            "notes": notes, "events": events, "my_assignment": my_assignment,
            "next_status": next_status, "error": request.query_params.get("error"),
            "can_set_black": case.status in (
                CaseStatus.FILED, CaseStatus.TRIAL, CaseStatus.JUDGED, CaseStatus.FINAL, CaseStatus.CLOSED
            ),
            "can_set_red": case.status in (CaseStatus.JUDGED, CaseStatus.FINAL, CaseStatus.CLOSED),
        },
    )


@app.post("/cases/{case_id}/advance")
def advance_case(case_id: int, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    case = _load_case_for(conn, case_id, lawyer)
    target = case.next_status()
    if target is None:
        conn.close()
        return _back_to_case(case_id, "เลื่อนสถานะต่อไม่ได้แล้ว")
    old = case.status
    try:
        if target == CaseStatus.CLOSED:
            appointments = appointment_repo.list_by_case(conn, case_id)
            open_appts = _open_appointments(appointments)
            if not case.can_close(
                has_future_appointments=any(not isinstance(a, FilingDeadline) for a in open_appts),
                has_pending_filing_deadlines=any(isinstance(a, FilingDeadline) for a in open_appts),
            ):
                raise InvalidStatusTransition("ปิดคดีไม่ได้ ยังมีนัดหรือกำหนดยื่นเอกสารที่ยังไม่เสร็จ (BR-9)")
        case.advance_status(target)
    except InvalidStatusTransition as e:
        conn.close()
        return _back_to_case(case_id, str(e))
    case_repo.update_progress(conn, case)
    case_repo.add_event(
        conn, case_id, lawyer, "status",
        f"เลื่อนสถานะ {case_status_th(old)} → {case_status_th(case.status)}",
    )
    conn.close()
    return _back_to_case(case_id)


@app.post("/cases/{case_id}/case-no")
def set_case_number(
    case_id: int, kind: str = Form(...), value: str = Form(...),
    lawyer: Lawyer = Depends(require_role(Lawyer)),
):
    """ใส่/แก้เลขคดีดำ (kind=black) หรือแดง (kind=red) — เลขซ้ำกับคดีอื่นขึ้น error ไทยแทน 500 จาก UNIQUE"""
    if kind not in ("black", "red"):
        raise HTTPException(400, "kind ต้องเป็น black หรือ red")
    conn = get_connection()
    case = _load_case_for(conn, case_id, lawyer)
    label = "ดำ" if kind == "black" else "แดง"
    old_value = case.black_case_no if kind == "black" else case.red_case_no
    try:
        if kind == "black":
            case.assign_black_number(value)
        else:
            case.assign_red_number(value)
        case_repo.update_progress(conn, case)
    except (InvalidStatusTransition, ValueError) as e:
        conn.close()
        return _back_to_case(case_id, str(e))
    except mysql.connector.IntegrityError:
        conn.close()
        return _back_to_case(case_id, f"หมายเลขคดี{label} {value.strip()} ซ้ำกับคดีอื่นในระบบ")
    new_value = case.black_case_no if kind == "black" else case.red_case_no
    case_repo.add_event(
        conn, case_id, lawyer, f"{kind}_no", f"หมายเลขคดี{label}: {old_value or '-'} → {new_value}"
    )
    conn.close()
    return _back_to_case(case_id)


@app.post("/cases/{case_id}/notes")
def add_case_note(case_id: int, text: str = Form(...), lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    _load_case_for(conn, case_id, lawyer)
    try:
        text = CaseNote.validate_text(text)
    except ValueError as e:
        conn.close()
        return _back_to_case(case_id, str(e))
    case_repo.add_note(conn, CaseNote(case_id=case_id, author=lawyer, text=text, created_at=datetime.now()))
    conn.close()
    return _back_to_case(case_id)


def _own_note(conn, case_id: int, note_id: int, lawyer: Lawyer) -> CaseNote:
    _load_case_for(conn, case_id, lawyer)
    note = case_repo.get_note(conn, note_id)
    if note is None or note.case_id != case_id:
        conn.close()
        raise HTTPException(404, "ไม่พบโน้ต")
    if not note.can_modify(lawyer):
        conn.close()
        raise HTTPException(403, "แก้หรือลบได้เฉพาะโน้ตของตัวเอง")
    return note


@app.post("/cases/{case_id}/notes/{note_id}/edit")
def edit_case_note(
    case_id: int, note_id: int, text: str = Form(...), lawyer: Lawyer = Depends(require_role(Lawyer))
):
    conn = get_connection()
    note = _own_note(conn, case_id, note_id, lawyer)
    try:
        note.text = CaseNote.validate_text(text)
    except ValueError as e:
        conn.close()
        return _back_to_case(case_id, str(e))
    case_repo.update_note(conn, note)
    conn.close()
    return _back_to_case(case_id)


@app.post("/cases/{case_id}/notes/{note_id}/delete")
def delete_case_note(case_id: int, note_id: int, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    _own_note(conn, case_id, note_id, lawyer)
    case_repo.delete_note(conn, note_id)
    conn.close()
    return _back_to_case(case_id)


def _my_accepted_assignment(case, lawyer: Lawyer):
    return next(
        (a for a in case._assignments if a.lawyer.id == lawyer.id and a.status.value == "accepted"), None
    )


@app.post("/cases/{case_id}/withdraw")
def request_withdraw(
    case_id: int, reason_code: str = Form(...), note: str = Form(""),
    lawyer: Lawyer = Depends(require_role(Lawyer)),
):
    conn = get_connection()
    case = _load_case_for(conn, case_id, lawyer)
    assignment = _my_accepted_assignment(case, lawyer)
    try:
        assignment.request_withdraw(reason_code, note)
    except (AssignmentError, ValueError) as e:
        conn.close()
        return _back_to_case(case_id, str(e))
    assignment_repo.update_status(conn, assignment)
    detail = f"ขอถอนตัว: {WITHDRAW_REASONS[reason_code]}" + (f" — {assignment.withdraw_note}" if assignment.withdraw_note else "")
    case_repo.add_event(conn, case_id, lawyer, "withdraw_request", detail)
    conn.close()
    return _back_to_case(case_id)


def _render_withdraw_review(request, conn, assignment, manager, *, error=None, warning=None, form=None):
    case = assignment.case
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    appts = appointment_repo.list_open_by_case_and_lawyer(conn, case.id, assignment.lawyer.id)
    workloads = [(lw, w) for lw, w in _lawyer_workloads(conn) if lw.id != assignment.lawyer.id]
    return templates.TemplateResponse(
        "manager/withdraw_review.html",
        {
            "request": request, "assignment": assignment, "case": case, "appointments": appts,
            "workloads": workloads, "threshold": WORKLOAD_OVERLOAD_THRESHOLD,
            "error": error, "warning": warning, "form": form or {},
        },
    )


@app.get("/manager/withdrawals/{assignment_id}", response_class=HTMLResponse)
def withdraw_review(request: Request, assignment_id: int, manager: Manager = Depends(require_role(Manager))):
    conn = get_connection()
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or not assignment.is_withdraw_requested():
        conn.close()
        raise HTTPException(404, "ไม่พบคำขอถอนตัวที่รออนุมัติ")
    response = _render_withdraw_review(request, conn, assignment, manager)
    conn.close()
    return response


@app.post("/manager/withdrawals/{assignment_id}/approve", response_class=HTMLResponse)
async def withdraw_approve(
    request: Request, assignment_id: int, manager: Manager = Depends(require_role(Manager)),
):
    """อนุมัติถอนตัว + (ถ้าเลือก) มอบหมายทนายคนใหม่ขั้นเดียว · นัดของทนายเดิมแต่ละรายการเลือก keep/transfer/cancel
    ตรวจทุกอย่างให้ผ่านก่อนเขียน DB — ผิดข้อใดข้อหนึ่งไม่มีอะไรถูกบันทึกครึ่งๆ กลางๆ
    """
    form = dict(await request.form())
    conn = get_connection()
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or not assignment.is_withdraw_requested():
        conn.close()
        raise HTTPException(404, "ไม่พบคำขอถอนตัวที่รออนุมัติ")
    case = assignment.case
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    old_lawyer, was_lead = assignment.lawyer, assignment.is_lead

    new_lawyer_id = form.get("new_lawyer_id") or ""
    new_lawyer = user_repo.get_by_id(conn, int(new_lawyer_id)) if new_lawyer_id else None
    if new_lawyer is not None and not isinstance(new_lawyer, Lawyer):
        conn.close()
        raise HTTPException(400, "ต้องเลือกทนายเท่านั้น")

    if new_lawyer is not None and form.get("confirm_overload") != "true":
        workload = _workload_for(conn, new_lawyer)
        if workload >= WORKLOAD_OVERLOAD_THRESHOLD:
            response = _render_withdraw_review(
                request, conn, assignment, manager, form=form,
                warning=(
                    f"{new_lawyer.display_name()} มีภาระงาน {workload} รายการ "
                    f"(เกินเกณฑ์ {WORKLOAD_OVERLOAD_THRESHOLD}) ยืนยันจะมอบหมายต่อไหม?"
                ),
            )
            conn.close()
            return response

    appts = appointment_repo.list_open_by_case_and_lawyer(conn, case.id, old_lawyer.id)
    choices = {a.id: form.get(f"appt_{a.id}", "keep") for a in appts}
    to_transfer = [a for a in appts if choices[a.id] == "transfer"]
    to_cancel = [a for a in appts if choices[a.id] == "cancel"]
    error = None
    new_assignment = None
    if to_transfer and new_lawyer is None:
        error = "ต้องเลือกทนายคนใหม่ก่อน จึงจะย้ายนัดได้"
    if error is None and new_lawyer is not None:
        try:
            new_assignment = LawFirm().assign_lawyer(case, new_lawyer, assigned_by=manager, is_lead=was_lead)
        except AssignmentError as e:  # BR-17: เช่นเลือกทนายคนเดิม หรือทนายที่มีรายการค้างอยู่แล้ว
            error = str(e)
    if error is None and to_transfer:
        schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, new_lawyer.id))
        for a in to_transfer:
            probe = replace(a, lawyer=new_lawyer)
            conflicts = schedule.find_conflicts(probe)
            if conflicts:
                error = (
                    f"ย้ายนัด {a.kind_label()} {thaidate(a.starts_at, 'datetime')} ไม่ได้ "
                    f"{new_lawyer.display_name()} มีนัดชนเวลา {thaidate(conflicts[0].starts_at, 'datetime')} (BR-1)"
                )
                break
            schedule.appointments.append(probe)
    if error is not None:
        # ประกอบ assignment ใหม่ที่ยังไม่บันทึกออกจากรายการของคดี ไม่ให้ค้างในหน้า review
        case._assignments[:] = [x for x in case._assignments if x is not new_assignment]
        response = _render_withdraw_review(request, conn, assignment, manager, error=error, form=form)
        conn.close()
        return response

    assignment.approve_withdraw()
    assignment_repo.update_status(conn, assignment)
    if new_assignment is not None:
        assignment_repo.add(conn, new_assignment)
    for a in to_transfer:
        appointment_repo.reassign(conn, a, new_lawyer)
    for a in to_cancel:
        appointment_repo.cancel(conn, a, f"{old_lawyer.display_name()}ถอนตัวจากคดี")
    detail = f"อนุมัติคำขอถอนตัวของ{old_lawyer.display_name()}"
    if new_lawyer is not None:
        detail += f" · มอบหมาย{new_lawyer.display_name()}" + (" เป็นทนายหลัก" if was_lead else "") + " (รอตอบรับ)"
    if to_transfer or to_cancel:
        detail += f" · นัด: ย้าย {len(to_transfer)} ยกเลิก {len(to_cancel)}"
    case_repo.add_event(conn, case.id, manager, "withdraw_approved", detail)
    conn.close()
    return RedirectResponse("/manager/dashboard#notify-withdraw", status_code=303)


@app.post("/manager/withdrawals/{assignment_id}/reject", response_class=HTMLResponse)
def withdraw_reject(
    request: Request, assignment_id: int, reason: str = Form(""),
    manager: Manager = Depends(require_role(Manager)),
):
    conn = get_connection()
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or not assignment.is_withdraw_requested():
        conn.close()
        raise HTTPException(404, "ไม่พบคำขอถอนตัวที่รออนุมัติ")
    try:
        assignment.reject_withdraw(reason)
    except ValueError as e:
        response = _render_withdraw_review(request, conn, assignment, manager, error=str(e))
        conn.close()
        return response
    assignment_repo.update_status(conn, assignment)
    case_repo.add_event(
        conn, assignment.case.id, manager, "withdraw_rejected",
        f"ไม่อนุมัติคำขอถอนตัวของ{assignment.lawyer.display_name()}: {assignment.withdraw_reject_reason}",
    )
    conn.close()
    return RedirectResponse("/manager/dashboard#notify-withdraw", status_code=303)


@app.get("/reminders", response_class=HTMLResponse)
def reminders(request: Request, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, lawyer.id))
    conn.close()
    items = schedule.upcoming_reminders(lawyer, date.today())
    return templates.TemplateResponse(
        "reminders/list.html", {"request": request, "lawyer": lawyer, "items": items}
    )


@app.post("/reminders/{appointment_id}/done")
def mark_reminder_done(appointment_id: int, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    appt = appointment_repo.get_by_id(conn, appointment_id)
    if appt is None or appt.lawyer.id != lawyer.id:
        conn.close()
        raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
    appointment_repo.mark_done(conn, appt)
    conn.close()
    return RedirectResponse("/reminders", status_code=303)
