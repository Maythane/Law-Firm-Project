"""BL-26/BL-31/BL-40: dashboard, คดีต่อทนาย, เพิ่มคดี, มอบหมาย, อนุมัติ/ไม่อนุมัติคำขอถอนตัว — manager เท่านั้น"""

from dataclasses import replace
from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import require_role
from api.deps import _lawyer_workloads, _workload_for, get_db, templates, thaidate
from domain.assignment import AssignmentError
from domain.case import Case, CaseStatus
from domain.firm import LawFirm
from domain.person import Client, Lawyer, Manager
from domain.schedule import Schedule
from repository import appointment_repo, assignment_repo, case_repo, client_repo, user_repo

router = APIRouter()

WORKLOAD_OVERLOAD_THRESHOLD = 15  # ponytail: เกณฑ์ตายตัวเลือกเอง (ดูจากการกระจายจริงใน seed.sql: 10-28) ไม่มีสเปกกำหนดตัวเลข ปรับได้ทีหลังถ้าต้องแม่นกว่านี้


@router.get("/manager/dashboard", response_class=HTMLResponse)
def manager_dashboard(request: Request, manager: Manager = Depends(require_role(Manager)), conn=Depends(get_db)):
    unassigned_cases = case_repo.list_without_accepted_lawyer(conn)
    waiting = assignment_repo.list_pending_for_cases(conn, unassigned_cases)
    declined = assignment_repo.list_unresolved_declined(conn)
    withdraw_requests = assignment_repo.list_withdraw_requests(conn)
    workloads = _lawyer_workloads(conn)
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


@router.get("/manager/lawyers/{lawyer_id}", response_class=HTMLResponse)
def lawyer_cases(
    request: Request, lawyer_id: int, manager: Manager = Depends(require_role(Manager)), tab: str = "active",
    conn=Depends(get_db),
):
    """คดีที่ทนายคนหนึ่งดูแลอยู่ + ความคืบหน้า — manager ดูอย่างเดียว (แก้/มอบหมายทำที่หน้าเดิม)"""
    lawyer = user_repo.get_by_id(conn, lawyer_id)
    if not isinstance(lawyer, Lawyer):
        raise HTTPException(404, "ไม่พบทนาย")
    assignments = assignment_repo.list_accepted_for_lawyer(conn, lawyer.id)
    workload = _workload_for(conn, lawyer)
    appointments = appointment_repo.list_by_lawyer(conn, lawyer.id)
    latest = case_repo.latest_event_by_case(conn, [a.case.id for a in assignments])

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


@router.get("/manager/cases/new", response_class=HTMLResponse)
def new_case_form(request: Request, manager: Manager = Depends(require_role(Manager)), conn=Depends(get_db)):
    clients = client_repo.list_all(conn)
    return templates.TemplateResponse(
        "manager/new_case.html",
        {
            "request": request, "manager": manager, "clients": clients, "error": None,
            "values": {}, "today": date.today().isoformat(),
        },
    )


@router.post("/manager/cases/new", response_class=HTMLResponse)
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
    conn=Depends(get_db),
):
    """BL-31: เลือกลูกความเดิม (client_id) หรือเพิ่มลูกความใหม่ (new_client_name ไม่ว่าง) — เลือกได้ทางใดทางหนึ่ง"""
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
    return RedirectResponse(f"/cases/{case.id}", status_code=303)


def _notify_back(back: str) -> str:
    """กล่องแจ้งเตือนที่ dashboard manager จะเปิดค้างไว้หลังจัดการเสร็จ — รับเฉพาะสองค่านี้ (ค่าอื่นใช้ unassigned)"""
    return back if back in ("declined", "unassigned") else "unassigned"


@router.get("/manager/cases/{case_id}/assign", response_class=HTMLResponse)
def assign_form(
    request: Request, case_id: int, manager: Manager = Depends(require_role(Manager)), back: str = "",
    conn=Depends(get_db),
):
    case = case_repo.get_by_id(conn, case_id)
    if case is None:
        raise HTTPException(404, "ไม่พบคดี")
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    workloads = _lawyer_workloads(conn)
    return templates.TemplateResponse(
        "manager/assign.html",
        {
            "request": request, "case": case, "workloads": workloads,
            "threshold": WORKLOAD_OVERLOAD_THRESHOLD, "error": None, "warning": None,
            "back": _notify_back(back),
        },
    )


@router.post("/manager/cases/{case_id}/assign", response_class=HTMLResponse)
def assign_submit(
    request: Request,
    case_id: int,
    manager: Manager = Depends(require_role(Manager)),
    lawyer_id: int = Form(...),
    is_lead: bool = Form(False),
    confirm_overload: str = Form(""),
    back: str = Form(""),
    conn=Depends(get_db),
):
    back = _notify_back(back)
    case = case_repo.get_by_id(conn, case_id)
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    lawyer = user_repo.get_by_id(conn, lawyer_id)
    workload = _workload_for(conn, lawyer)

    if workload >= WORKLOAD_OVERLOAD_THRESHOLD and confirm_overload != "true":
        workloads = _lawyer_workloads(conn)
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
        return templates.TemplateResponse(
            "manager/assign.html",
            {
                "request": request, "case": case, "workloads": workloads,
                "threshold": WORKLOAD_OVERLOAD_THRESHOLD, "error": str(e), "warning": None, "back": back,
            },
        )
    assignment_repo.add(conn, assignment)
    return RedirectResponse(f"/manager/dashboard#notify-{back}", status_code=303)


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


@router.get("/manager/withdrawals/{assignment_id}", response_class=HTMLResponse)
def withdraw_review(request: Request, assignment_id: int, manager: Manager = Depends(require_role(Manager)), conn=Depends(get_db)):
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or not assignment.is_withdraw_requested():
        raise HTTPException(404, "ไม่พบคำขอถอนตัวที่รออนุมัติ")
    return _render_withdraw_review(request, conn, assignment, manager)


@router.post("/manager/withdrawals/{assignment_id}/approve", response_class=HTMLResponse)
async def withdraw_approve(
    request: Request, assignment_id: int, manager: Manager = Depends(require_role(Manager)),
    conn=Depends(get_db),
):
    """อนุมัติถอนตัว + (ถ้าเลือก) มอบหมายทนายคนใหม่ขั้นเดียว · นัดของทนายเดิมแต่ละรายการเลือก keep/transfer/cancel
    ตรวจทุกอย่างให้ผ่านก่อนเขียน DB — ผิดข้อใดข้อหนึ่งไม่มีอะไรถูกบันทึกครึ่งๆ กลางๆ
    """
    form = dict(await request.form())
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or not assignment.is_withdraw_requested():
        raise HTTPException(404, "ไม่พบคำขอถอนตัวที่รออนุมัติ")
    case = assignment.case
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    old_lawyer, was_lead = assignment.lawyer, assignment.is_lead

    new_lawyer_id = form.get("new_lawyer_id") or ""
    new_lawyer = user_repo.get_by_id(conn, int(new_lawyer_id)) if new_lawyer_id else None
    if new_lawyer is not None and not isinstance(new_lawyer, Lawyer):
        raise HTTPException(400, "ต้องเลือกทนายเท่านั้น")

    if new_lawyer is not None and form.get("confirm_overload") != "true":
        workload = _workload_for(conn, new_lawyer)
        if workload >= WORKLOAD_OVERLOAD_THRESHOLD:
            return _render_withdraw_review(
                request, conn, assignment, manager, form=form,
                warning=(
                    f"{new_lawyer.display_name()} มีภาระงาน {workload} รายการ "
                    f"(เกินเกณฑ์ {WORKLOAD_OVERLOAD_THRESHOLD}) ยืนยันจะมอบหมายต่อไหม?"
                ),
            )

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
        return _render_withdraw_review(request, conn, assignment, manager, error=error, form=form)

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
    return RedirectResponse("/manager/dashboard#notify-withdraw", status_code=303)


@router.post("/manager/withdrawals/{assignment_id}/reject", response_class=HTMLResponse)
def withdraw_reject(
    request: Request, assignment_id: int, reason: str = Form(""),
    manager: Manager = Depends(require_role(Manager)), conn=Depends(get_db),
):
    assignment = assignment_repo.get_by_id(conn, assignment_id)
    if assignment is None or not assignment.is_withdraw_requested():
        raise HTTPException(404, "ไม่พบคำขอถอนตัวที่รออนุมัติ")
    try:
        assignment.reject_withdraw(reason)
    except ValueError as e:
        return _render_withdraw_review(request, conn, assignment, manager, error=str(e))
    assignment_repo.update_status(conn, assignment)
    case_repo.add_event(
        conn, assignment.case.id, manager, "withdraw_rejected",
        f"ไม่อนุมัติคำขอถอนตัวของ{assignment.lawyer.display_name()}: {assignment.withdraw_reject_reason}",
    )
    return RedirectResponse("/manager/dashboard#notify-withdraw", status_code=303)
