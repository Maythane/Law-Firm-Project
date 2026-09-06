"""BL-20: FastAPI + Jinja2 + Pico.css/HTMX — หน้าแรกคือตารางวันนี้
BL-21: หน้าคดี + หน้าเตือน — ตรวจสิทธิ์ผ่าน user.can_view_case() จุดเดียว (BR-15)
BL-25: ล็อกอิน + session (signed cookie) + require_role() — ทุก route ที่รู้ตัวตนผ่าน dependency นี้จุดเดียว
BL-26: หน้ามอบหมายของ manager + ตารางภาระงานทนาย
BL-27: กล่องคดีรอการตอบรับบน dashboard ทนาย — อัปเดตด้วย HTMX เฉพาะกล่องนั้น
BL-28: ปฏิทินรายเดือนของทนาย — จิ้มวันแล้วไปหน้าตารางวันนั้น
BL-29: หน้าจัดการผู้ใช้ของ admin — เพิ่ม/ปิดใช้งาน/รีเซ็ตรหัสผ่าน (ลบไม่ได้ เพราะมีนัด/การมอบหมายอ้างอิงอยู่)
ดูขอบเขตงานเต็มที่ backlog.md#bl-20, #bl-21, #bl-25, #bl-26, #bl-27, #bl-28, #bl-29
"""

import calendar
from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.auth import SESSION_COOKIE, authenticate, create_session_cookie, hash_password, require_role
from domain.appointment import ClientMeeting, CourtHearing, FilingDeadline
from domain.errors import AssignmentError, ScheduleConflictError
from domain.firm import LawFirm
from domain.person import Admin, Lawyer, Manager, SystemUser
from domain.schedule import Schedule
from repository import appointment_repo, assignment_repo, case_repo, user_repo
from repository.db import get_connection

WORKLOAD_OVERLOAD_THRESHOLD = 15  # ponytail: เกณฑ์ตายตัวเลือกเอง (ดูจากการกระจายจริงใน seed.sql: 10-28) ไม่มีสเปกกำหนดตัวเลข ปรับได้ทีหลังถ้าต้องแม่นกว่านี้

app = FastAPI(title="ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ")
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
    recently_declined = assignment_repo.list_recently_declined(conn)
    workloads = _lawyer_workloads(conn)
    conn.close()
    return templates.TemplateResponse(
        "dashboard/manager.html",
        {
            "request": request, "manager": manager, "unassigned_cases": unassigned_cases,
            "recently_declined": recently_declined, "workloads": workloads,
        },
    )


@app.get("/manager/cases/{case_id}/assign", response_class=HTMLResponse)
def assign_form(request: Request, case_id: int, manager: Manager = Depends(require_role(Manager))):
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
):
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
                "pending_lawyer_id": lawyer_id, "pending_is_lead": is_lead,
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
                "threshold": WORKLOAD_OVERLOAD_THRESHOLD, "error": str(e), "warning": None,
            },
        )
    assignment_repo.add(conn, assignment)
    conn.close()
    return RedirectResponse(f"/cases/{case_id}", status_code=303)


@app.get("/admin/dashboard")
def admin_dashboard(admin: Admin = Depends(require_role(Admin))):
    return RedirectResponse("/admin/users")


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, admin: Admin = Depends(require_role(Admin))):
    conn = get_connection()
    users = user_repo.list_all(conn)
    conn.close()
    return templates.TemplateResponse(
        "admin/users.html", {"request": request, "admin": admin, "users": users, "error": None},
    )


@app.post("/admin/users", response_class=HTMLResponse)
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
        users = user_repo.list_all(conn)
        conn.close()
        return templates.TemplateResponse(
            "admin/users.html",
            {"request": request, "admin": admin, "users": users, "error": f'ชื่อผู้ใช้ "{username}" มีอยู่แล้ว'},
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


@app.post("/admin/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int, admin: Admin = Depends(require_role(Admin)), new_password: str = Form(...),
):
    conn = get_connection()
    user_repo.set_password_hash(conn, user_id, hash_password(new_password))
    conn.close()
    return RedirectResponse("/admin/users", status_code=303)


@app.get("/schedule/today", response_class=HTMLResponse)
def schedule_today(request: Request, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    schedule = Schedule(appointments=appointment_repo.list_by_lawyer(conn, lawyer.id))
    pending = assignment_repo.list_pending_for_lawyer(conn, lawyer.id)
    conn.close()
    today = date.today()
    appointments = schedule.day_view(lawyer, today)
    return templates.TemplateResponse(
        "schedule/today.html",
        {"request": request, "lawyer": lawyer, "appointments": appointments, "today": today, "pending": pending},
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

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return templates.TemplateResponse(
        "schedule/month.html",
        {
            "request": request, "lawyer": lawyer, "year": year, "month": month,
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
    conn.close()
    return templates.TemplateResponse("schedule/_pending_box.html", {"request": request, "pending": pending})


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
        conn.close()
        return templates.TemplateResponse(
            "schedule/_pending_box.html",
            {
                "request": request, "pending": pending,
                "decline_error": str(e), "error_assignment_id": assignment_id,
            },
        )
    assignment_repo.update_status(conn, assignment)
    pending = assignment_repo.list_pending_for_lawyer(conn, lawyer.id)
    conn.close()
    return templates.TemplateResponse("schedule/_pending_box.html", {"request": request, "pending": pending})


@app.get("/schedule/new", response_class=HTMLResponse)
def new_appointment_form(request: Request, lawyer: Lawyer = Depends(require_role(Lawyer))):
    conn = get_connection()
    cases = case_repo.list_accepted_by_lawyer(conn, lawyer.id)
    conn.close()
    return templates.TemplateResponse(
        "schedule/form.html",
        {"request": request, "lawyer": lawyer, "cases": cases, "error": None, "values": {}},
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


@app.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: int, current_user: SystemUser = Depends(require_role())):
    conn = get_connection()
    case = case_repo.get_by_id(conn, case_id)
    if case is None:
        conn.close()
        raise HTTPException(404, "ไม่พบคดี")
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    if not current_user.can_view_case(case):
        conn.close()
        raise HTTPException(403, "ไม่มีสิทธิ์เข้าถึงคดีนี้")  # BR-15
    appointments = sorted(appointment_repo.list_by_case(conn, case_id), key=lambda a: a.starts_at)
    conn.close()
    return templates.TemplateResponse(
        "cases/detail.html",
        {"request": request, "case": case, "appointments": appointments, "user": current_user},
    )


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
