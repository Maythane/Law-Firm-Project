# BL-18 — เทสนี้ต่อฐานข้อมูลจริง (lawfirm-db ผ่าน XAMPP) ต่างจากเทสอื่นในโฟลเดอร์นี้ที่ไม่ต้องต่อ DB
# ถ้า XAMPP/MariaDB ไม่ได้รันอยู่ เทสไฟล์นี้จะ fail ที่ setup ไม่ใช่ error สุ่ม

from datetime import date, datetime

import pytest

from domain.appointment import CourtHearing
from domain.case import Case, CaseStatus
from domain.person import Client, Lawyer, Manager
from repository import appointment_repo, case_repo, client_repo, user_repo
from repository.db import get_connection
from api.auth import authenticate, hash_password


@pytest.fixture
def conn():
    connection = get_connection()
    cur = connection.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ("appointment_changes", "appointments", "case_assignments", "cases", "clients", "users"):
        cur.execute(f"TRUNCATE TABLE {table}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    connection.commit()
    yield connection
    connection.close()


def test_add_and_read_back_court_hearing_appointment(conn):
    manager = user_repo.add(conn, Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089", username="manager1"))
    lawyer = user_repo.add(
        conn,
        Lawyer(name="สมชาย", citizen_id="1", phone="080", username="lawyer1", license_no="L1"),
    )
    client = client_repo.add(conn, Client(name="สมหญิง", citizen_id="2", phone="081"))
    case = case_repo.add(
        conn,
        Case(
            title="ผิดสัญญาซื้อขาย",
            client=client,
            client_role="โจทก์",
            opposing_party="บจก. คู่กรณี",
            court_name="ศาลแพ่งกรุงเทพใต้",
            opened_date=date(2026, 1, 1),
        ),
    )
    hearing = appointment_repo.add(
        conn,
        CourtHearing(
            case=case, lawyer=lawyer,
            starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
            location="ศาลแพ่งกรุงเทพใต้", court_name="ศาลแพ่งกรุงเทพใต้", room_no="401",
        ),
    )

    loaded = appointment_repo.get_by_id(conn, hearing.id)

    assert isinstance(loaded, CourtHearing)
    assert loaded.reminder_lead_days() == 3
    assert loaded.case.title == "ผิดสัญญาซื้อขาย"
    assert loaded.lawyer.display_name() == "ทนายสมชาย"


def test_case_status_round_trips_without_replaying_state_machine(conn):
    client = client_repo.add(conn, Client(name="สมหญิง", citizen_id="2", phone="081"))
    saved = case_repo.add(
        conn,
        Case(
            title="ผิดสัญญาซื้อขาย", client=client, client_role="โจทก์",
            opposing_party="บจก. คู่กรณี", court_name="ศาลแพ่งกรุงเทพใต้",
            opened_date=date(2026, 1, 1), black_case_no="1234/2568",
        ),
    )

    loaded = case_repo.find_by_case_no(conn, "1234/2568")

    assert loaded.status == CaseStatus.OPEN
    assert loaded.id == saved.id


def test_authenticate_accepts_correct_username_and_password(conn):
    user_repo.add(conn, Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1",
    ))

    user = authenticate("lawyer1", "password123")

    assert user is not None
    assert user.username == "lawyer1"


def test_authenticate_rejects_wrong_password(conn):
    user_repo.add(conn, Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1",
    ))

    assert authenticate("lawyer1", "wrong-password") is None


def test_authenticate_rejects_inactive_account(conn):
    user_repo.add(conn, Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1", is_active=False,
    ))

    assert authenticate("lawyer1", "password123") is None
