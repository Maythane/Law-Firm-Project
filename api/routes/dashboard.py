"""ทางแยกหลังล็อกอินตามบทบาท + หน้า style guide (ไม่ต้องล็อกอิน ไม่ใช่ฟีเจอร์ระบบ)"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import require_role
from api.deps import templates
from domain.person import Admin, Lawyer, Manager, SystemUser

router = APIRouter()


@router.get("/style-guide", response_class=HTMLResponse)
def style_guide(request: Request):
    """หน้าอ้างอิงโทเค็นสี/spacing/component สด — ไม่ใช่ฟีเจอร์ของระบบ อยู่นอกขอบเขต backlog เหมือน tools/generate_seed.py"""
    return templates.TemplateResponse("style_guide.html", {"request": request})


@router.get("/dashboard")
def dashboard(current_user: SystemUser = Depends(require_role())):
    if isinstance(current_user, Lawyer):
        return RedirectResponse("/schedule/today")
    if isinstance(current_user, Manager):
        return RedirectResponse("/manager/dashboard")
    return RedirectResponse("/admin/dashboard")
