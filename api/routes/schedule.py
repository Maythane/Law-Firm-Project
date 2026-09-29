"""BL-20/BL-27/BL-28/BL-32/BL-35: ตารางวันนี้, รายวัน, ปฏิทินเดือน, รับ/ปฏิเสธคดี, เพิ่มนัด — ทนายเท่านั้น"""

import calendar
from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import require_role
from api.deps import _workload_for, get_db, templates
from domain.appointment import ClientMeeting, CourtHearing, FilingDeadline
from domain.assignment import AssignmentError
from domain.errors import ScheduleConflictError
from domain.person import Lawyer
from domain.schedule import Schedule
from repository.appointment_repo import AppointmentRepository
from repository.assignment_repo import AssignmentRepository
from repository.case_repo import CaseRepository

router = APIRouter()


def _month_neighbors(year: int, month: int) -> tuple[int, int, int, int]:
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return prev_year, prev_month, next_year, next_month


@router.get("/schedule/today", response_class=HTMLResponse)
def schedule_today(
    request: Request,
    lawyer: Lawyer = Depends(require_role(Lawyer)),
    year: int | None = None,
    month: int | None = None,
    conn=Depends(get_db),
):
    """BL-32: ปฏิทินเดือนขึ้นบนสุด — คลิกแต่ละนัดเปิด popup ข้อมูลคดี ไม่ใช่ navigate เหมือน /schedule/month"""
    today = date.today()
    cal_year = year or today.year
    cal_month = month or today.month
    schedule = Schedule(appointments=AppointmentRepository(conn).list_by_lawyer(lawyer.id))
    pending = AssignmentRepository(conn).list_pending_for_lawyer(lawyer.id)
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


@router.get("/schedule/day", response_class=HTMLResponse)
def schedule_day(
    request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)), d: str | None = None,
    conn=Depends(get_db),
):
    target_day = date.fromisoformat(d) if d else date.today()
    schedule = Schedule(appointments=AppointmentRepository(conn).list_by_lawyer(lawyer.id))
    appointments = schedule.day_view(lawyer, target_day)
    return templates.TemplateResponse(
        "schedule/day.html",
        {"request": request, "lawyer": lawyer, "appointments": appointments, "day": target_day},
    )


@router.get("/schedule/month", response_class=HTMLResponse)
def schedule_month(
    request: Request,
    lawyer: Lawyer = Depends(require_role(Lawyer)),
    year: int | None = None,
    month: int | None = None,
    conn=Depends(get_db),
):
    today = date.today()
    year = year or today.year
    month = month or today.month
    schedule = Schedule(appointments=AppointmentRepository(conn).list_by_lawyer(lawyer.id))
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


@router.post("/assignments/{assignment_id}/accept", response_class=HTMLResponse)
def accept_assignment(
    request: Request, assignment_id: int, lawyer: Lawyer = Depends(require_role(Lawyer)),
    conn=Depends(get_db),
):
    assignments = AssignmentRepository(conn)
    assignment = assignments.get_by_id(assignment_id)
    if assignment is None or assignment.lawyer.id != lawyer.id:
        raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
    try:
        assignment.accept()
    except AssignmentError as e:
        raise HTTPException(409, str(e))
    assignments.update_status(assignment)
    pending = assignments.list_pending_for_lawyer(lawyer.id)
    workload = _workload_for(conn, lawyer)
    return templates.TemplateResponse(
        "schedule/_pending_swap_response.html", {"request": request, "pending": pending, "workload": workload}
    )


@router.post("/assignments/{assignment_id}/decline", response_class=HTMLResponse)
def decline_assignment(
    request: Request,
    assignment_id: int,
    reason: str = Form(...),
    lawyer: Lawyer = Depends(require_role(Lawyer)),
    conn=Depends(get_db),
):
    assignments = AssignmentRepository(conn)
    assignment = assignments.get_by_id(assignment_id)
    if assignment is None or assignment.lawyer.id != lawyer.id:
        raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
    try:
        assignment.decline(reason)
    except ValueError as e:
        pending = assignments.list_pending_for_lawyer(lawyer.id)
        workload = _workload_for(conn, lawyer)
        return templates.TemplateResponse(
            "schedule/_pending_swap_response.html",
            {
                "request": request, "pending": pending, "workload": workload,
                "decline_error": str(e), "error_assignment_id": assignment_id,
            },
        )
    assignments.update_status(assignment)
    pending = assignments.list_pending_for_lawyer(lawyer.id)
    workload = _workload_for(conn, lawyer)
    return templates.TemplateResponse(
        "schedule/_pending_swap_response.html", {"request": request, "pending": pending, "workload": workload}
    )


@router.get("/schedule/new", response_class=HTMLResponse)
def new_appointment_form(
    request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)), case_id: int | None = None,
    conn=Depends(get_db),
):
    """case_id เลือกล่วงหน้าได้ผ่าน query — ปุ่ม "ลงนัดถัดไป" จาก popup ปฏิทิน (BL-32)"""
    cases = CaseRepository(conn).list_accepted_by_lawyer(lawyer.id)
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


@router.post("/schedule/new", response_class=HTMLResponse)
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
    conn=Depends(get_db),
):
    cases = CaseRepository(conn)
    case = cases.get_by_id(case_id)
    case._assignments.extend(AssignmentRepository(conn).list_for_case(case))

    appt = _build_appointment(
        kind, case, lawyer,
        datetime.fromisoformat(starts_at), datetime.fromisoformat(ends_at),
        location, court_name, room_no, triggered_by_event,
    )
    appointments = AppointmentRepository(conn)
    schedule = Schedule(appointments=appointments.list_by_lawyer(lawyer.id))
    try:
        schedule.add(appt)
    except (ScheduleConflictError, AssignmentError) as e:
        cases = cases.list_accepted_by_lawyer(lawyer.id)
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
    appointments.add(appt)
    return RedirectResponse("/schedule/today", status_code=303)
