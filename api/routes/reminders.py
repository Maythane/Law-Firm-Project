"""BL-35: รายการเตือนใกล้ครบกำหนด + กดทำแล้ว — ทนายเท่านั้น"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import require_role
from api.deps import get_db, templates
from domain.person import Lawyer
from domain.schedule import Schedule
from repository.appointment_repo import AppointmentRepository

router = APIRouter()


@router.get("/reminders", response_class=HTMLResponse)
def reminders(request: Request, lawyer: Lawyer = Depends(require_role(Lawyer)), conn=Depends(get_db)):
    schedule = Schedule(appointments=AppointmentRepository(conn).list_by_lawyer(lawyer.id))
    items = schedule.upcoming_reminders(lawyer, date.today())
    return templates.TemplateResponse(
        "reminders/list.html", {"request": request, "lawyer": lawyer, "items": items}
    )


@router.post("/reminders/{appointment_id}/done")
def mark_reminder_done(
    appointment_id: int, lawyer: Lawyer = Depends(require_role(Lawyer)), conn=Depends(get_db),
):
    appointments = AppointmentRepository(conn)
    appt = appointments.get_by_id(appointment_id)
    if appt is None or appt.lawyer.id != lawyer.id:
        raise HTTPException(403, "ไม่มีสิทธิ์ทำรายการนี้")
    appointments.mark_done(appt)
    return RedirectResponse("/reminders", status_code=303)
