# BL-18 — เทสนี้ต่อฐานแยก lawfirm_test (TEST_DB_NAME) ไม่แตะ lawfirm-db ของแอป
# ถ้า MariaDB ไม่ได้รันอยู่ เทสไฟล์นี้จะ fail ที่ setup ไม่ใช่ error สุ่ม

import os
from datetime import date, datetime

import mysql.connector
import pytest

from domain.appointment import CourtHearing
from domain.assignment import AssignmentStatus, CaseAssignment
from domain.case import Case, CaseNote, CaseStatus
from domain.person import Client, Lawyer, Manager
from repository.appointment_repo import AppointmentRepository
from repository.assignment_repo import AssignmentRepository
from repository.case_repo import CaseRepository
from repository.client_repo import ClientRepository
from repository.user_repo import UserRepository
from repository.db import TEST_DB_NAME, get_test_connection, is_test_db_allowed
from api.auth import authenticate, hash_password


@pytest.fixture
def conn():
    app_db = os.environ.get("DB_NAME", "lawfirm-db")
    if not is_test_db_allowed(TEST_DB_NAME, app_db):
        pytest.fail(f"ชื่อฐานเทส ({TEST_DB_NAME}) ชนฐานแอป ({app_db}) หรือ lawfirm-db — ปฏิเสธ TRUNCATE")
    connection = get_test_connection()
    cur = connection.cursor()
    cur.execute("SELECT DATABASE()")
    assert cur.fetchone()[0] == TEST_DB_NAME, "เทสต้องวิ่งบนฐานเทสเท่านั้น"
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ("case_events", "case_notes", "appointment_changes", "appointments", "case_assignments", "cases", "clients", "users"):
        cur.execute(f"TRUNCATE TABLE {table}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    connection.commit()
    yield connection
    connection.close()


def test_add_and_read_back_court_hearing_appointment(conn):
    users, clients, cases, appointments = (
        UserRepository(conn), ClientRepository(conn), CaseRepository(conn), AppointmentRepository(conn),
    )
    manager = users.add(Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089", username="manager1"))
    lawyer = users.add(
        Lawyer(name="สมชาย", citizen_id="1", phone="080", username="lawyer1", license_no="L1"),
    )
    client = clients.add(Client(name="สมหญิง", citizen_id="2", phone="081"))
    case = cases.add(
        Case(
            title="ผิดสัญญาซื้อขาย",
            client=client,
            client_role="โจทก์",
            opposing_party="บจก. คู่กรณี",
            court_name="ศาลแพ่งกรุงเทพใต้",
            opened_date=date(2026, 1, 1),
        ),
    )
    hearing = appointments.add(
        CourtHearing(
            case=case, lawyer=lawyer,
            starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
            location="ศาลแพ่งกรุงเทพใต้", court_name="ศาลแพ่งกรุงเทพใต้", room_no="401",
        ),
    )

    loaded = appointments.get_by_id(hearing.id)

    assert isinstance(loaded, CourtHearing)
    assert loaded.reminder_lead_days() == 3
    assert loaded.case.title == "ผิดสัญญาซื้อขาย"
    assert loaded.lawyer.display_name() == "ทนายสมชาย"


def test_case_status_round_trips_without_replaying_state_machine(conn):
    clients, cases = ClientRepository(conn), CaseRepository(conn)
    client = clients.add(Client(name="สมหญิง", citizen_id="2", phone="081"))
    saved = cases.add(
        Case(
            title="ผิดสัญญาซื้อขาย", client=client, client_role="โจทก์",
            opposing_party="บจก. คู่กรณี", court_name="ศาลแพ่งกรุงเทพใต้",
            opened_date=date(2026, 1, 1), black_case_no="1234/2568",
        ),
    )

    loaded = cases.find_by_case_no("1234/2568")

    assert loaded.status == CaseStatus.OPEN
    assert loaded.id == saved.id


def test_authenticate_accepts_correct_username_and_password(conn):
    UserRepository(conn).add(Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1",
    ))

    user = authenticate("lawyer1", "password123", conn)

    assert user is not None
    assert user.username == "lawyer1"


def test_authenticate_rejects_wrong_password(conn):
    UserRepository(conn).add(Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1",
    ))

    assert authenticate("lawyer1", "wrong-password", conn) is None


def test_list_all_clients_returns_every_client_sorted_by_name(conn):
    clients = ClientRepository(conn)
    clients.add(Client(name="วิชัย", citizen_id="3", phone="082"))
    clients.add(Client(name="กมล", citizen_id="4", phone="083"))

    all_clients = clients.list_all()

    assert [c.name for c in all_clients] == ["กมล", "วิชัย"]


def test_authenticate_rejects_inactive_account(conn):
    UserRepository(conn).add(Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1", is_active=False,
    ))

    assert authenticate("lawyer1", "password123", conn) is None


def _case_with_accepted_lawyer(conn):
    users, clients, cases, assignments = (
        UserRepository(conn), ClientRepository(conn), CaseRepository(conn), AssignmentRepository(conn),
    )
    manager = users.add(Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089", username="manager1"))
    lawyer = users.add(Lawyer(name="สมชาย", citizen_id="1", phone="080", username="lawyer1", license_no="L1"))
    client = clients.add(Client(name="สมหญิง", citizen_id="2", phone="081"))
    case = cases.add(Case(
        title="ผิดสัญญาซื้อขาย", client=client, client_role="โจทก์", opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่ง", opened_date=date(2026, 1, 1),
    ))
    assignment = assignments.add(CaseAssignment(
        case=case, lawyer=lawyer, assigned_by=manager, assigned_at=datetime.now(),
        status=AssignmentStatus.ACCEPTED, is_lead=True,
    ))
    return manager, lawyer, case, assignment


def test_withdraw_request_round_trips_and_shows_in_manager_list(conn):
    assignments, cases = AssignmentRepository(conn), CaseRepository(conn)
    manager, lawyer, case, assignment = _case_with_accepted_lawyer(conn)
    assert assignments.list_withdraw_requests() == []

    assignment.request_withdraw("other", "ป่วย")
    assignments.update_status(assignment)

    loaded = assignments.get_by_id(assignment.id)
    assert loaded.is_withdraw_requested() and loaded.withdraw_note == "ป่วย"
    assert [a.id for a in assignments.list_withdraw_requests()] == [assignment.id]
    # ระหว่างรอ ยังนับเป็นคดีของทนายอยู่ (คดีของฉัน)
    assert [a.case.id for a in assignments.list_accepted_for_lawyer(lawyer.id)] == [case.id]

    loaded.approve_withdraw()
    assignments.update_status(loaded)
    assert assignments.list_accepted_for_lawyer(lawyer.id) == []
    assert [c.id for c in cases.list_without_accepted_lawyer()] == [case.id]


def test_update_progress_and_duplicate_black_number_raises_integrity_error(conn):
    cases = CaseRepository(conn)
    _, _, case, _ = _case_with_accepted_lawyer(conn)
    other = cases.add(Case(
        title="อีกคดี", client=case.client, client_role="จำเลย", opposing_party="x",
        court_name="ศาล", opened_date=date(2026, 1, 2), black_case_no="1/2569",
    ))
    case._status = CaseStatus.FILED
    case.assign_black_number("2/2569")
    cases.update_progress(case)
    assert cases.get_by_id(case.id).black_case_no == "2/2569"

    case.assign_black_number(other.black_case_no)
    with pytest.raises(mysql.connector.IntegrityError):
        cases.update_progress(case)


def test_notes_and_events_round_trip(conn):
    cases = CaseRepository(conn)
    manager, lawyer, case, _ = _case_with_accepted_lawyer(conn)
    note = cases.add_note(CaseNote(case_id=case.id, author=lawyer, text="ก", created_at=datetime.now()))
    note.text = "แก้"
    cases.update_note(note)
    assert [n.text for n in cases.list_notes(case.id)] == ["แก้"]
    cases.delete_note(note.id)
    assert cases.get_note(note.id) is None

    cases.add_event(case.id, manager, "status", "เลื่อนสถานะ")
    events = cases.list_events(case.id)
    assert events[0].detail == "เลื่อนสถานะ" and events[0].actor.id == manager.id


def test_unresolved_declined_disappears_once_case_has_pending_or_accepted_lawyer(conn):
    users, assignments = UserRepository(conn), AssignmentRepository(conn)
    manager, lawyer, case, _ = _case_with_accepted_lawyer(conn)
    # ล้างทนายที่ตอบรับ แล้วสร้างการปฏิเสธ: คดีค้าง → ต้องขึ้นในรายการ
    cur = conn.cursor()
    cur.execute("DELETE FROM case_assignments")
    conn.commit()
    declined = assignments.add(CaseAssignment(
        case=case, lawyer=lawyer, assigned_by=manager, assigned_at=datetime.now(),
    ))
    declined.decline("ภาระงานล้น")
    assignments.update_status(declined)
    assert [a.id for a in assignments.list_unresolved_declined()] == [declined.id]

    # มอบหมายทนายคนใหม่ (pending) แล้ว การปฏิเสธเก่าไม่ค้างอีก
    other = users.add(Lawyer(name="สมศักดิ์", citizen_id="5", phone="083", username="lawyer2", license_no="L2"))
    assignments.add(CaseAssignment(case=case, lawyer=other, assigned_by=manager, assigned_at=datetime.now()))
    assert assignments.list_unresolved_declined() == []


def test_latest_event_by_case_returns_most_recent_only(conn):
    cases = CaseRepository(conn)
    manager, _, case, _ = _case_with_accepted_lawyer(conn)
    assert cases.latest_event_by_case([]) == {}
    assert cases.latest_event_by_case([case.id]) == {}
    cases.add_event(case.id, manager, "status", "เหตุการณ์แรก")
    cases.add_event(case.id, manager, "status", "เหตุการณ์ล่าสุด")
    assert cases.latest_event_by_case([case.id])[case.id][0] == "เหตุการณ์ล่าสุด"


def test_without_accepted_lawyer_keeps_case_while_lawyer_is_pending_and_lists_who_waits(conn):
    cases, assignments = CaseRepository(conn), AssignmentRepository(conn)
    manager, lawyer, case, assignment = _case_with_accepted_lawyer(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM case_assignments")
    conn.commit()
    assert [c.id for c in cases.list_without_accepted_lawyer()] == [case.id]
    assert assignments.list_pending_for_cases([case]) == {}

    pending = assignments.add(CaseAssignment(
        case=case, lawyer=lawyer, assigned_by=manager, assigned_at=datetime.now(),
    ))
    # ยังไม่มีทนายตอบรับ (แค่รอตอบ) → ยังต้องอยู่ในกล่องแจ้งเตือน พร้อมรู้ว่ารอใคร
    assert [c.id for c in cases.list_without_accepted_lawyer()] == [case.id]
    waiting = assignments.list_pending_for_cases([case])
    assert [a.id for a in waiting[case.id]] == [pending.id]

    pending.accept()
    assignments.update_status(pending)
    assert cases.list_without_accepted_lawyer() == []
