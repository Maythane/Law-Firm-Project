"""BL-25: ล็อกอิน + session (signed cookie) + require_role()

ดูขอบเขตงานเต็มที่ backlog.md#bl-25

hash_password()/verify_password() ทำไว้ก่อนตอน BL-19 (scrypt ของ stdlib + salt ต่อผู้ใช้)
ส่วน session ใช้ itsdangerous (มีอยู่แล้วใน requirements.txt) เซ็นคุกกี้ ไม่เก็บ state ฝั่งเซิร์ฟเวอร์
"""

import hashlib
import os

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from domain.person import SystemUser
from repository.user_repo import UserRepository
from repository.db import get_connection

_N, _R, _P = 2**14, 8, 1  # พารามิเตอร์ scrypt มาตรฐาน — เร็วพอสำหรับ dev ไม่ต้องจูนเพิ่ม

SESSION_COOKIE = "session"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 ชั่วโมง
_SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
_serializer = URLSafeTimedSerializer(_SECRET_KEY)


def hash_password(raw: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(raw.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"{salt.hex()}:{derived.hex()}"


def verify_password(raw: str, stored: str) -> bool:
    salt_hex, hash_hex = stored.split(":", 1)
    derived = hashlib.scrypt(raw.encode(), salt=bytes.fromhex(salt_hex), n=_N, r=_R, p=_P)
    return derived.hex() == hash_hex


def create_session_cookie(user_id: int) -> str:
    return _serializer.dumps(user_id)


def read_session_cookie(token: str) -> int | None:
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def authenticate(username: str, password: str) -> SystemUser | None:
    """คืน user ถ้า username/password ถูกต้องและบัญชียัง is_active · ผิดข้อใดข้อหนึ่งคืน None"""
    conn = get_connection()
    user = UserRepository(conn).find_by_username(username)
    conn.close()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def require_role(*allowed_roles: type):
    """FastAPI dependency ตัวเดียวที่ทุก route ใช้ — ไม่ผ่านคืน 403 เสมอ (ไม่ใช่หน้าเปล่า)

    เรียกแบบ Depends(require_role()) สำหรับ "ต้องล็อกอินเฉยๆ ไม่จำกัดบทบาท"
    หรือ Depends(require_role(Manager)) สำหรับ "ต้องเป็น Manager เท่านั้น"
    """

    def dependency(request: Request) -> SystemUser:
        token = request.cookies.get(SESSION_COOKIE)
        user_id = read_session_cookie(token) if token else None
        if user_id is None:
            raise HTTPException(403, "กรุณาเข้าสู่ระบบ")
        conn = get_connection()
        user = UserRepository(conn).get_by_id(user_id)
        conn.close()
        if user is None or not user.is_active:
            raise HTTPException(403, "บัญชีถูกปิดใช้งานหรือไม่พบผู้ใช้")
        if allowed_roles and not isinstance(user, allowed_roles):
            raise HTTPException(403, "ไม่มีสิทธิ์เข้าถึงหน้านี้")
        return user

    return dependency
