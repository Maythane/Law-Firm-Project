# BL-30 (tests/test_assignment.py) ตาม backlog.md#bl-30
from datetime import date, datetime

import pytest

from domain.assignment import AssignmentStatus, CaseAssignment
from domain.case import Case, CaseStatus
from domain.errors import AssignmentError, InvalidStatusTransition
from domain.firm import LawFirm
from domain.person import Admin, Client, Lawyer, Manager
from domain.schedule import Schedule
from domain.appointment import ClientMeeting


def make_case(**overrides):
    defaults = dict(
        title="ผิดสัญญาซื้อขาย",
        client=Client(name="สมหญิง", citizen_id="2", phone="081"),
        client_role="โจทก์",
        opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่งกรุงเทพใต้",
        opened_date=date(2026, 1, 1),
    )
    defaults.update(overrides)
    return Case(**defaults)


def make_manager():
    return Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")


def make_lawyer(citizen_id="1"):
    return Lawyer(name="สมชาย", citizen_id=citizen_id, phone="080", license_no="L1")


def test_accept_from_pending_succeeds():
    assignment = CaseAssignment(
        case=make_case(), lawyer=make_lawyer(), assigned_by=make_manager(),
        assigned_at=datetime.now(),
    )
    assignment.accept()
    assert assignment.status == AssignmentStatus.ACCEPTED
    assert assignment.responded_at is not None


def test_accept_twice_raises():
    assignment = CaseAssignment(
        case=make_case(), lawyer=make_lawyer(), assigned_by=make_manager(),
        assigned_at=datetime.now(),
    )
    assignment.accept()
    with pytest.raises(AssignmentError):
        assignment.accept()


def test_decline_without_reason_raises():
    assignment = CaseAssignment(
        case=make_case(), lawyer=make_lawyer(), assigned_by=make_manager(),
        assigned_at=datetime.now(),
    )
    with pytest.raises(ValueError):
        assignment.decline("")


def test_decline_with_reason_succeeds():
    assignment = CaseAssignment(
        case=make_case(), lawyer=make_lawyer(), assigned_by=make_manager(),
        assigned_at=datetime.now(),
    )
    assignment.decline("ภาระงานเต็มแล้ว")
    assert assignment.status == AssignmentStatus.DECLINED
    assert assignment.decline_reason == "ภาระงานเต็มแล้ว"


def test_decline_after_already_declined_raises():
    assignment = CaseAssignment(
        case=make_case(), lawyer=make_lawyer(), assigned_by=make_manager(),
        assigned_at=datetime.now(),
    )
    assignment.decline("ภาระงานเต็มแล้ว")
    with pytest.raises(AssignmentError):
        assignment.decline("เหตุผลอื่น")


def test_reassigning_same_lawyer_while_pending_or_accepted_raises():
    # BR-17
    firm = LawFirm()
    case = make_case()
    manager = make_manager()
    lawyer = make_lawyer()
    firm.assign_lawyer(case, lawyer, assigned_by=manager)  # ยัง PENDING

    with pytest.raises(AssignmentError):
        firm.assign_lawyer(case, lawyer, assigned_by=manager)


def test_reassigning_after_decline_is_allowed():
    firm = LawFirm()
    case = make_case()
    manager = make_manager()
    lawyer = make_lawyer()
    first = firm.assign_lawyer(case, lawyer, assigned_by=manager)
    first.decline("ภาระงานเต็มแล้ว")

    second = firm.assign_lawyer(case, lawyer, assigned_by=manager)  # มอบหมายใหม่ได้
    assert second.status == AssignmentStatus.PENDING


def test_case_cannot_advance_to_filed_without_any_accepted_lawyer():
    # BR-18
    case = make_case()
    with pytest.raises(InvalidStatusTransition):
        case.advance_status(CaseStatus.FILED)


def test_case_advances_to_filed_once_a_lawyer_accepts():
    firm = LawFirm()
    case = make_case()
    firm.open_case(case)
    manager = make_manager()
    lawyer = make_lawyer()
    firm.assign_lawyer(case, lawyer, assigned_by=manager).accept()

    case.advance_status(CaseStatus.FILED)
    assert case.status == CaseStatus.FILED


def test_schedule_add_rejects_appointment_for_lawyer_who_has_not_accepted():
    # BR-19
    case = make_case()
    lawyer = make_lawyer()
    schedule = Schedule()
    appt = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="สำนักงาน",
    )
    with pytest.raises(AssignmentError):
        schedule.add(appt)


def test_can_view_case_correct_for_all_three_roles():
    # BR-15
    firm = LawFirm()
    case = make_case()
    firm.open_case(case)
    manager = make_manager()
    lawyer = make_lawyer()
    other_lawyer = make_lawyer(citizen_id="3")
    admin = Admin(name="แอดมิน", citizen_id="5", phone="084")
    firm.assign_lawyer(case, lawyer, assigned_by=manager).accept()

    assert lawyer.can_view_case(case) is True
    assert other_lawyer.can_view_case(case) is False
    assert manager.can_view_case(case) is True
    assert admin.can_view_case(case) is False
