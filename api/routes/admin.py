"""BL-29/BL-37/BL-39: dashboard สถิติ, รายชื่อผู้ใช้, เพิ่ม/ปิดใช้งาน/แก้โปรไฟล์ — admin เท่านั้น"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.auth import hash_password, require_role
from api.deps import get_db, templates
from domain.person import Admin, Lawyer, Manager
from repository.user_repo import UserRepository

router = APIRouter()


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, admin: Admin = Depends(require_role(Admin)), conn=Depends(get_db)):
    """BL-39: สถิติผู้ใช้ 3 บทบาท แยกเปิด/ปิดใช้งาน — สำนักเดียว ไม่มีสถิติคดี (อยู่ที่ manager dashboard แทน)"""
    counts = UserRepository(conn).count_by_role()
    return templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "admin": admin, "counts": counts},
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(
    request: Request, admin: Admin = Depends(require_role(Admin)),
    error: str | None = None, conn=Depends(get_db),
):
    users = UserRepository(conn).list_all()
    return templates.TemplateResponse(
        "admin/users.html", {"request": request, "admin": admin, "users": users, "error": error},
    )


@router.get("/admin/users/new", response_class=HTMLResponse)
def admin_new_user_form(request: Request, admin: Admin = Depends(require_role(Admin))):
    return templates.TemplateResponse(
        "admin/users_new.html", {"request": request, "admin": admin, "error": None, "values": {}},
    )


@router.post("/admin/users/new", response_class=HTMLResponse)
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
    conn=Depends(get_db),
):
    if UserRepository(conn).find_by_username(username) is not None:
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
    UserRepository(conn).add(new_user)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/toggle-active")
def admin_toggle_active(user_id: int, admin: Admin = Depends(require_role(Admin)), conn=Depends(get_db)):
    users = UserRepository(conn)
    user = users.get_by_id(user_id)
    if user is None:
        raise HTTPException(404, "ไม่พบผู้ใช้")
    users.set_active(user_id, not user.is_active)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/{user_id}/edit", response_class=HTMLResponse)
def admin_edit_user(
    request: Request,
    user_id: int,
    admin: Admin = Depends(require_role(Admin)),
    name: str = Form(...),
    username: str = Form(...),
    new_password: str = Form(""),
    conn=Depends(get_db),
):
    """BL-37: แก้ชื่อที่ใช้แสดง/username/รหัสผ่าน (เว้นว่าง = ไม่เปลี่ยน) — รวมกับรีเซ็ตรหัสผ่านเดิมเป็นฟอร์มเดียว ไม่แก้ role"""
    users = UserRepository(conn)
    existing = users.find_by_username(username)
    if existing is not None and existing.id != user_id:
        return admin_users(request, admin, error=f'ชื่อผู้ใช้ "{username}" มีอยู่แล้ว', conn=conn)
    password_hash = hash_password(new_password) if new_password.strip() else None
    users.update_profile(user_id, name, username, password_hash)
    return RedirectResponse("/admin/users", status_code=303)
