# BL-18 — เทสนี้ต่อฐานข้อมูลจริง (lawfirm-db ผ่าน XAMPP) ต่างจากเทสอื่นในโฟลเดอร์นี้ที่ไม่ต้องต่อ DB
# ถ้า XAMPP/MariaDB ไม่ได้รันอยู่ เทสไฟล์นี้จะ fail ที่ setup ไม่ใช่ error สุ่ม

from datetime import date, datetime

import mysql.connector
import pytest

from domain.appointment import CourtHearing
from domain.assignment import AssignmentStatus, CaseAssignment
from domain.case import Case, CaseNote, CaseStatus
from domain.person import Client, Lawyer, Manager
from repository import appointment_repo, assignment_repo, case_repo, client_repo, user_repo
from repository.db import get_connection
from api.auth import authenticate, hash_password


@pytest.fixture
def conn():
    connection = get_connection()
    cur = connection.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ("case_events", "case_notes", "appointment_changes", "appointments", "case_assignments", "cases", "clients", "users"):
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


def test_list_all_clients_returns_every_client_sorted_by_name(conn):
    client_repo.add(conn, Client(name="วิชัย", citizen_id="3", phone="082"))
    client_repo.add(conn, Client(name="กมล", citizen_id="4", phone="083"))

    clients = client_repo.list_all(conn)

    assert [c.name for c in clients] == ["กมล", "วิชัย"]


def test_authenticate_rejects_inactive_account(conn):
    user_repo.add(conn, Lawyer(
        name="สมชาย", citizen_id="1", phone="080", username="lawyer1",
        password_hash=hash_password("password123"), license_no="L1", is_active=False,
    ))

    assert authenticate("lawyer1", "password123") is None


def _case_with_accepted_lawyer(conn):
    manager = user_repo.add(conn, Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089", username="manager1"))
    lawyer = user_repo.add(conn, Lawyer(name="สมชาย", citizen_id="1", phone="080", username="lawyer1", license_no="L1"))
    client = client_repo.add(conn, Client(name="สมหญิง", citizen_id="2", phone="081"))
    case = case_repo.add(conn, Case(
        title="ผิดสัญญาซื้อขาย", client=client, client_role="โจทก์", opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่ง", opened_date=date(2026, 1, 1),
    ))
    assignment = assignment_repo.add(conn, CaseAssignment(
        case=case, lawyer=lawyer, assigned_by=manager, assigned_at=datetime.now(),
        status=AssignmentStatus.ACCEPTED, is_lead=True,
    ))
    return manager, lawyer, case, assignment


def test_withdraw_request_round_trips_and_shows_in_manager_list(conn):
    manager, lawyer, case, assignment = _case_with_accepted_lawyer(conn)
    assert assignment_repo.list_withdraw_requests(conn) == []

    assignment.request_withdraw("other", "ป่วย")
    assignment_repo.update_status(conn, assignment)

    loaded = assignment_repo.get_by_id(conn, assignment.id)
    assert loaded.is_withdraw_requested() and loaded.withdraw_note == "ป่วย"
    assert [a.id for a in assignment_repo.list_withdraw_requests(conn)] == [assignment.id]
    # ระหว่างรอ ยังนับเป็นคดีของทนายอยู่ (คดีของฉัน)
    assert [a.case.id for a in assignment_repo.list_accepted_for_lawyer(conn, lawyer.id)] == [case.id]

    loaded.approve_withdraw()
    assignment_repo.update_status(conn, loaded)
    assert assignment_repo.list_accepted_for_lawyer(conn, lawyer.id) == []
    assert [c.id for c in case_repo.list_without_accepted_lawyer(conn)] == [case.id]


def test_update_progress_and_duplicate_black_number_raises_integrity_error(conn):
    _, _, case, _ = _case_with_accepted_lawyer(conn)
    other = case_repo.add(conn, Case(
        title="อีกคดี", client=case.client, client_role="จำเลย", opposing_party="x",
        court_name="ศาล", opened_date=date(2026, 1, 2), black_case_no="1/2569",
    ))
    case._status = CaseStatus.FILED
    case.assign_black_number("2/2569")
    case_repo.update_progress(conn, case)
    assert case_repo.get_by_id(conn, case.id).black_case_no == "2/2569"

    case.assign_black_number(other.black_case_no)
    with pytest.raises(mysql.connector.IntegrityError):
        case_repo.update_progress(conn, case)


def test_notes_and_events_round_trip(conn):
    manager, lawyer, case, _ = _case_with_accepted_lawyer(conn)
    note = case_repo.add_note(conn, CaseNote(case_id=case.id, author=lawyer, text="ก", created_at=datetime.now()))
    note.text = "แก้"
    case_repo.update_note(conn, note)
    assert [n.text for n in case_repo.list_notes(conn, case.id)] == ["แก้"]
    case_repo.delete_note(conn, note.id)
    assert case_repo.get_note(conn, note.id) is None

    case_repo.add_event(conn, case.id, manager, "status", "เลื่อนสถานะ")
    events = case_repo.list_events(conn, case.id)
    assert events[0].detail == "เลื่อนสถานะ" and events[0].actor.id == manager.id


def test_unresolved_declined_disappears_once_case_has_pending_or_accepted_lawyer(conn):
    manager, lawyer, case, _ = _case_with_accepted_lawyer(conn)
    # ล้างทนายที่ตอบรับ แล้วสร้างการปฏิเสธ: คดีค้าง → ต้องขึ้นในรายการ
    cur = conn.cursor()
    cur.execute("DELETE FROM case_assignments")
    conn.commit()
    declined = assignment_repo.add(conn, CaseAssignment(
        case=case, lawyer=lawyer, assigned_by=manager, assigned_at=datetime.now(),
    ))
    declined.decline("ภาระงานล้น")
    assignment_repo.update_status(conn, declined)
    assert [a.id for a in assignment_repo.list_unresolved_declined(conn)] == [declined.id]

    # มอบหมายทนายคนใหม่ (pending) แล้ว การปฏิเสธเก่าไม่ค้างอีก
    other = user_repo.add(conn, Lawyer(name="สมศักดิ์", citizen_id="5", phone="083", username="lawyer2", license_no="L2"))
    assignment_repo.add(conn, CaseAssignment(case=case, lawyer=other, assigned_by=manager, assigned_at=datetime.now()))
    assert assignment_repo.list_unresolved_declined(conn) == []


def test_latest_event_by_case_returns_most_recent_only(conn):
    manager, _, case, _ = _case_with_accepted_lawyer(conn)
    assert case_repo.latest_event_by_case(conn, []) == {}
    assert case_repo.latest_event_by_case(conn, [case.id]) == {}
    case_repo.add_event(conn, case.id, manager, "status", "เหตุการณ์แรก")
    case_repo.add_event(conn, case.id, manager, "status", "เหตุการณ์ล่าสุด")
    assert case_repo.latest_event_by_case(conn, [case.id])[case.id][0] == "เหตุการณ์ล่าสุด"


def test_without_accepted_lawyer_keeps_case_while_lawyer_is_pending_and_lists_who_waits(conn):
    manager, lawyer, case, assignment = _case_with_accepted_lawyer(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM case_assignments")
    conn.commit()
    assert [c.id for c in case_repo.list_without_accepted_lawyer(conn)] == [case.id]
    assert assignment_repo.list_pending_for_cases(conn, [case]) == {}

    pending = assignment_repo.add(conn, CaseAssignment(
        case=case, lawyer=lawyer, assigned_by=manager, assigned_at=datetime.now(),
    ))
    # ยังไม่มีทนายตอบรับ (แค่รอตอบ) → ยังต้องอยู่ในกล่องแจ้งเตือน พร้อมรู้ว่ารอใคร
    assert [c.id for c in case_repo.list_without_accepted_lawyer(conn)] == [case.id]
    waiting = assignment_repo.list_pending_for_cases(conn, [case])
    assert [a.id for a in waiting[case.id]] == [pending.id]

    pending.accept()
    assignment_repo.update_status(conn, pending)
    assert case_repo.list_without_accepted_lawyer(conn) == []
