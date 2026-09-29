"""BL-21/BL-40: คดีของฉัน, หน้าคดี, เลื่อนสถานะ, เลขคดี, โน้ต, ขอถอนตัว — ตรวจสิทธิ์ผ่าน user.can_view_case() จุดเดียว (BR-15)"""

from datetime import datetime
from urllib.parse import quote

import mysql.connector
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import require_role
from api.deps import case_status_th, get_db, templates
from domain.appointment import FilingDeadline
from domain.assignment import WITHDRAW_REASONS, AssignmentError
from domain.case import CaseNote, CaseStatus
from domain.errors import InvalidStatusTransition
from domain.person import Lawyer, SystemUser
from repository import appointment_repo, assignment_repo, case_repo

router = APIRouter()


def _load_case(conn, case_id: int):
    case = case_repo.get_by_id(conn, case_id)
    if case is None:
        raise HTTPException(404, "ไม่พบคดี")
    case._assignments.extend(assignment_repo.list_for_case(conn, case))
    return case


def _load_case_for(conn, case_id: int, user: SystemUser):
    """โหลดคดี + ตรวจสิทธิ์จุดเดียว (BR-15) — ทุก route ที่แตะคดีผ่านฟังก์ชันนี้"""
    case = _load_case(conn, case_id)
    if not user.can_view_case(case):
        raise HTTPException(403, "ไม่มีสิทธิ์เข้าถึงคดีนี้")
    return case


def _back_to_case(case_id: int, error: str | None = None) -> RedirectResponse:
    url = f"/cases/{case_id}" + (f"?error={quote(error)}" if error else "")
    return RedirectResponse(url, status_code=303)


def _open_appointments(appointments) -> list:
    """นัดที่ยังไม่ถึง/ยังไม่เสร็จ/ยังไม่ยกเลิก — ใช้ตรวจ BR-9 ตอนปิดคดี"""
    now = datetime.now()
    return [a for a in appointments if not a.is_cancelled and not a.is_done and a.starts_at >= now]


@router.get("/cases", response_class=HTMLResponse)
def my_cases(
    request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)),
    tab: str = "active", q: str = "", status: str = "",
    conn=Depends(get_db),
):
    """หน้า "คดีของฉัน" — คดีที่ตอบรับแล้ว แยกแท็บกำลังดำเนินการ / ปิดแล้ว-ยกเลิก เรียงตามนัดถัดไป"""
    assignments = assignment_repo.list_accepted_for_lawyer(conn, lawyer.id)
    appointments = appointment_repo.list_by_lawyer(conn, lawyer.id)

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


@router.get("/cases/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: int, current_user: SystemUser = Depends(require_role()), conn=Depends(get_db)):
    case = _load_case_for(conn, case_id, current_user)
    appointments = sorted(appointment_repo.list_by_case(conn, case_id), key=lambda a: a.starts_at)
    notes = case_repo.list_notes(conn, case_id)
    events = case_repo.list_events(conn, case_id)
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


@router.post("/cases/{case_id}/advance")
def advance_case(case_id: int, lawyer: Lawyer = Depends(require_role(Lawyer)), conn=Depends(get_db)):
    case = _load_case_for(conn, case_id, lawyer)
    target = case.next_status()
    if target is None:
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
        return _back_to_case(case_id, str(e))
    case_repo.update_progress(conn, case)
    case_repo.add_event(
        conn, case_id, lawyer, "status",
        f"เลื่อนสถานะ {case_status_th(old)} → {case_status_th(case.status)}",
    )
    return _back_to_case(case_id)


@router.post("/cases/{case_id}/case-no")
def set_case_number(
    case_id: int, kind: str = Form(...), value: str = Form(...),
    lawyer: Lawyer = Depends(require_role(Lawyer)), conn=Depends(get_db),
):
    """ใส่/แก้เลขคดีดำ (kind=black) หรือแดง (kind=red) — เลขซ้ำกับคดีอื่นขึ้น error ไทยแทน 500 จาก UNIQUE"""
    if kind not in ("black", "red"):
        raise HTTPException(400, "kind ต้องเป็น black หรือ red")
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
        return _back_to_case(case_id, str(e))
    except mysql.connector.IntegrityError:
        return _back_to_case(case_id, f"หมายเลขคดี{label} {value.strip()} ซ้ำกับคดีอื่นในระบบ")
    new_value = case.black_case_no if kind == "black" else case.red_case_no
    case_repo.add_event(
        conn, case_id, lawyer, f"{kind}_no", f"หมายเลขคดี{label}: {old_value or '-'} → {new_value}"
    )
    return _back_to_case(case_id)


@router.post("/cases/{case_id}/notes")
def add_case_note(
    case_id: int, text: str = Form(...), lawyer: Lawyer = Depends(require_role(Lawyer)),
    conn=Depends(get_db),
):
    _load_case_for(conn, case_id, lawyer)
    try:
        text = CaseNote.validate_text(text)
    except ValueError as e:
        return _back_to_case(case_id, str(e))
    case_repo.add_note(conn, CaseNote(case_id=case_id, author=lawyer, text=text, created_at=datetime.now()))
    return _back_to_case(case_id)


def _own_note(conn, case_id: int, note_id: int, lawyer: Lawyer) -> CaseNote:
    _load_case_for(conn, case_id, lawyer)
    note = case_repo.get_note(conn, note_id)
    if note is None or note.case_id != case_id:
        raise HTTPException(404, "ไม่พบโน้ต")
    if not note.can_modify(lawyer):
        raise HTTPException(403, "แก้หรือลบได้เฉพาะโน้ตของตัวเอง")
    return note


@router.post("/cases/{case_id}/notes/{note_id}/edit")
def edit_case_note(
    case_id: int, note_id: int, text: str = Form(...), lawyer: Lawyer = Depends(require_role(Lawyer)),
    conn=Depends(get_db),
):
    note = _own_note(conn, case_id, note_id, lawyer)
    try:
        note.text = CaseNote.validate_text(text)
    except ValueError as e:
        return _back_to_case(case_id, str(e))
    case_repo.update_note(conn, note)
    return _back_to_case(case_id)


@router.post("/cases/{case_id}/notes/{note_id}/delete")
def delete_case_note(
    case_id: int, note_id: int, lawyer: Lawyer = Depends(require_role(Lawyer)), conn=Depends(get_db),
):
    _own_note(conn, case_id, note_id, lawyer)
    case_repo.delete_note(conn, note_id)
    return _back_to_case(case_id)


def _my_accepted_assignment(case, lawyer: Lawyer):
    return next(
        (a for a in case._assignments if a.lawyer.id == lawyer.id and a.status.value == "accepted"), None
    )


@router.post("/cases/{case_id}/withdraw")
def request_withdraw(
    case_id: int, reason_code: str = Form(...), note: str = Form(""),
    lawyer: Lawyer = Depends(require_role(Lawyer)), conn=Depends(get_db),
):
    case = _load_case_for(conn, case_id, lawyer)
    assignment = _my_accepted_assignment(case, lawyer)
    try:
        assignment.request_withdraw(reason_code, note)
    except (AssignmentError, ValueError) as e:
        return _back_to_case(case_id, str(e))
    assignment_repo.update_status(conn, assignment)
    detail = f"ขอถอนตัว: {WITHDRAW_REASONS[reason_code]}" + (f" — {assignment.withdraw_note}" if assignment.withdraw_note else "")
    case_repo.add_event(conn, case_id, lawyer, "withdraw_request", detail)
    return _back_to_case(case_id)
