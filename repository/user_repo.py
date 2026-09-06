"""BL-18: repository ของตาราง users — อ่าน role แล้วสร้าง object ให้ตรงคลาส

ชั้น domain ต้องไม่ import อะไรจากที่นี่ (ทิศทางเดียว: repository -> domain)
"""

from domain.person import Admin, Lawyer, Manager, SystemUser

_ROLE_TO_CLASS = {"lawyer": Lawyer, "manager": Manager, "admin": Admin}


def _row_to_user(row: dict) -> SystemUser:
    cls = _ROLE_TO_CLASS[row["role"]]
    kwargs = dict(
        name=row["name"],
        citizen_id=row["citizen_id"],
        phone=row["phone"],
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        is_active=bool(row["is_active"]),
    )
    if cls is Lawyer:
        kwargs["license_no"] = row["license_no"] or ""
    return cls(**kwargs)


def get_by_id(conn, user_id: int) -> SystemUser | None:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    return _row_to_user(row) if row else None


def find_by_username(conn, username: str) -> SystemUser | None:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    return _row_to_user(row) if row else None


def list_by_role(conn, role: str) -> list[SystemUser]:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE role = %s AND is_active = 1 ORDER BY name", (role,))
    return [_row_to_user(row) for row in cur.fetchall()]


def list_all(conn) -> list[SystemUser]:
    """รายชื่อผู้ใช้ทั้งหมด รวมที่ปิดใช้งานแล้ว — หน้าจัดการผู้ใช้ของ admin (BL-29)"""
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users ORDER BY role, name")
    return [_row_to_user(row) for row in cur.fetchall()]


def set_active(conn, user_id: int, is_active: bool) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (is_active, user_id))
    conn.commit()


def set_password_hash(conn, user_id: int, password_hash: str) -> None:
    """รีเซ็ตรหัสผ่าน — admin ตั้งรหัสใหม่ให้ผู้ใช้ (BL-29)"""
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
    conn.commit()


def add(conn, user: SystemUser) -> SystemUser:
    role = {Lawyer: "lawyer", Manager: "manager", Admin: "admin"}[type(user)]
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users
           (role, name, citizen_id, phone, username, password_hash, license_no, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            role,
            user.name,
            user.citizen_id,
            user.phone,
            user.username,
            user.password_hash,
            getattr(user, "license_no", None),
            user.is_active,
        ),
    )
    conn.commit()
    user.id = cur.lastrowid
    return user
