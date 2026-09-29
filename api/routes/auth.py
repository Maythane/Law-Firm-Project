"""BL-25: route ล็อกอิน/ออกจากระบบ/แก้ไขบัญชีตัวเอง + หน้าแรกที่เด้งตาม session"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import (
    SESSION_COOKIE, authenticate, create_session_cookie, hash_password, require_role,
    verify_password,
)
from api.deps import get_db, templates
from domain.person import SystemUser
from repository.user_repo import UserRepository

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse("auth/login.html", {"request": request, "error": error})


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    user = authenticate(username, password)
    if user is None:
        return RedirectResponse("/login?error=1", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(SESSION_COOKIE, create_session_cookie(user.id), httponly=True)
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")


@router.post("/account/edit")
def account_edit(
    request: Request,
    current_user: SystemUser = Depends(require_role()),
    name: str = Form(...),
    username: str = Form(...),
    current_password: str = Form(""),
    new_password: str = Form(""),
    conn=Depends(get_db),
):
    """BL-38: self-service แก้ไขบัญชีตัวเอง (ทุกบทบาท) จากกล่องใน sidebar
    บังคับรหัสผ่านเดิมเฉพาะตอนเปลี่ยนรหัสผ่านใหม่จริง — แก้แค่ชื่อ/username ไม่ต้องยืนยันรหัสเดิม
    ฟอร์มฝังอยู่ใน layout.html ทุกหน้า เลยไม่มีหน้าเดียวให้ re-render ตอน error — ส่งกลับไปหน้าเดิม (referer) พร้อม query param แทน (แบบเดียวกับ /login?error=1)
    """
    back = request.headers.get("referer") or "/dashboard"
    sep = "&" if "?" in back else "?"
    password_hash = None
    if new_password.strip():
        if not verify_password(current_password, current_user.password_hash):
            return RedirectResponse(f"{back}{sep}account_error=รหัสผ่านเดิมไม่ถูกต้อง", status_code=303)
        password_hash = hash_password(new_password)
    users = UserRepository(conn)
    existing = users.find_by_username(username)
    if existing is not None and existing.id != current_user.id:
        return RedirectResponse(f"{back}{sep}account_error=ชื่อผู้ใช้นี้มีอยู่แล้ว", status_code=303)
    users.update_profile(current_user.id, name, username, password_hash)
    return RedirectResponse(back, status_code=303)
