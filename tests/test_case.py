from datetime import date, datetime

import pytest

from domain.assignment import AssignmentStatus, CaseAssignment
from domain.case import Case, CaseStatus
from domain.errors import AssignmentError, InvalidStatusTransition
from domain.person import Client, Lawyer, Manager


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


def give_case_an_accepted_lawyer(case: Case) -> None:
    """ทางลัดสำหรับเทส Case เพียวๆ — ตั้งสถานะตอบรับตรงๆ ไม่ผ่าน assign_lawyer (BR-18 ต้องมีทนายตอบรับก่อนยื่นฟ้อง)"""
    lawyer = Lawyer(name="สมชาย", citizen_id="99", phone="080", license_no="L1")
    case._assignments.append(
        CaseAssignment(
            case=case, lawyer=lawyer, assigned_by=None, assigned_at=datetime.now(),
            _status=AssignmentStatus.ACCEPTED,
        )
    )


def test_new_case_starts_at_open():
    case = make_case()
    assert case.status == CaseStatus.OPEN


def test_advance_status_moves_one_step_at_a_time():
    case = make_case()
    give_case_an_accepted_lawyer(case)
    case.advance_status(CaseStatus.FILED)
    assert case.status == CaseStatus.FILED
    case.advance_status(CaseStatus.TRIAL)
    assert case.status == CaseStatus.TRIAL


def test_advance_status_skipping_a_step_raises():
    case = make_case()
    with pytest.raises(InvalidStatusTransition):
        case.advance_status(CaseStatus.TRIAL)  # ข้าม FILED


def test_advance_status_from_cancelled_raises():
    case = make_case()
    case.cancel("ลูกความถอนฟ้อง")
    with pytest.raises(InvalidStatusTransition):
        case.advance_status(CaseStatus.FILED)


def test_assign_red_number_before_judged_raises():
    case = make_case()
    give_case_an_accepted_lawyer(case)
    case.advance_status(CaseStatus.FILED)
    with pytest.raises(InvalidStatusTransition):
        case.assign_red_number("999/2569")


def test_assign_red_number_after_judged_succeeds():
    case = make_case()
    give_case_an_accepted_lawyer(case)
    for status in (CaseStatus.FILED, CaseStatus.TRIAL, CaseStatus.JUDGED):
        case.advance_status(status)
    case.assign_red_number("999/2569")
    assert case.display_red_no() == "999/2569"


def test_cancel_requires_reason():
    case = make_case()
    with pytest.raises(ValueError):
        case.cancel("")


def test_cancel_then_reopen_restores_previous_status():
    case = make_case()
    give_case_an_accepted_lawyer(case)
    case.advance_status(CaseStatus.FILED)
    case.cancel("รอเจรจา")
    assert case.status == CaseStatus.CANCELLED
    case.reopen("เจรจาไม่สำเร็จ กลับมาว่าความต่อ")
    assert case.status == CaseStatus.FILED


def test_cancel_not_allowed_when_already_closed():
    case = make_case()
    give_case_an_accepted_lawyer(case)
    for status in (
        CaseStatus.FILED,
        CaseStatus.TRIAL,
        CaseStatus.JUDGED,
        CaseStatus.FINAL,
        CaseStatus.CLOSED,
    ):
        case.advance_status(status)
    with pytest.raises(InvalidStatusTransition):
        case.cancel("เปลี่ยนใจ")


def test_can_close_false_when_future_items_pending():
    case = make_case()
    assert case.can_close(has_future_appointments=True, has_pending_filing_deadlines=False) is False
    assert case.can_close(has_future_appointments=False, has_pending_filing_deadlines=True) is False
    assert case.can_close(has_future_appointments=False, has_pending_filing_deadlines=False) is True


def test_black_number_only_from_filed():
    case = make_case()
    with pytest.raises(InvalidStatusTransition):
        case.assign_black_number("ผ.1/2569")
    give_case_an_accepted_lawyer(case)
    case.advance_status(CaseStatus.FILED)
    case.assign_black_number(" ผ.1/2569 ")
    assert case.black_case_no == "ผ.1/2569"
    case.assign_black_number("ผ.2/2569")  # แก้เลขที่ใส่ผิดได้
    assert case.black_case_no == "ผ.2/2569"


def test_black_and_red_number_reject_blank():
    case = make_case(_status=CaseStatus.JUDGED)
    with pytest.raises(ValueError):
        case.assign_black_number(" ")
    with pytest.raises(ValueError):
        case.assign_red_number("")


def test_case_note_only_author_can_modify():
    from domain.case import CaseNote
    author = Lawyer(name="ก", citizen_id="1", phone="0", license_no="L", id=1)
    other = Lawyer(name="ข", citizen_id="2", phone="0", license_no="L", id=2)
    note = CaseNote(case_id=1, author=author, text="x", created_at=datetime.now())
    assert note.can_modify(author) and not note.can_modify(other)
    with pytest.raises(ValueError):
        CaseNote.validate_text("  ")


def test_reassigning_same_lawyer_while_pending_or_accepted_raises():
    # BR-17 — คดีเป็นเจ้าของกฎนี้ (ย้ายจาก LawFirm.assign_lawyer)
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    case.assign_lawyer(lawyer, assigned_by=manager)  # ยัง PENDING

    with pytest.raises(AssignmentError):
        case.assign_lawyer(lawyer, assigned_by=manager)


def test_reassigning_after_decline_is_allowed():
    # BR-17 — รายการเดิมจบแล้ว (DECLINED) มอบหมายใหม่ได้
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    first = case.assign_lawyer(lawyer, assigned_by=manager)
    first.decline("ภาระงานเต็มแล้ว")

    second = case.assign_lawyer(lawyer, assigned_by=manager)  # มอบหมายใหม่ได้
    assert second.status == AssignmentStatus.PENDING


def test_withdrawn_lawyer_can_be_assigned_again():
    # BR-17 — รายการเดิมจบแล้ว (WITHDRAWN) ไม่โยน error
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    a = case.assign_lawyer(lawyer, assigned_by=manager)
    a.accept()
    a.request_withdraw("overload")
    a.approve_withdraw()
    case.assign_lawyer(lawyer, assigned_by=manager)


def test_assign_lawyer_supports_three_lawyers_with_lead():
    # BL-14 (many-to-many + 1 lead): lawyers()/lead_lawyer() นับเฉพาะที่ ACCEPTED แล้ว
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lead = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")
    second = Lawyer(name="สมศักดิ์", citizen_id="3", phone="082", license_no="L2")
    third = Lawyer(name="สมหมาย", citizen_id="4", phone="083", license_no="L3")

    case.assign_lawyer(lead, assigned_by=manager, is_lead=True).accept()
    case.assign_lawyer(second, assigned_by=manager).accept()
    case.assign_lawyer(third, assigned_by=manager).accept()

    assert len(case.lawyers()) == 3
    assert case.lead_lawyer() is lead


def test_assign_lawyer_only_counts_accepted_ones():
    case = make_case()
    manager = Manager(name="ผู้จัดการหนึ่ง", citizen_id="90", phone="089")
    lawyer = Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")

    case.assign_lawyer(lawyer, assigned_by=manager)  # ยังไม่กดรับ

    assert case.lawyers() == []
    assert case.lead_lawyer() is None


def test_next_status_follows_order_and_stops():
    case = make_case()
    assert case.next_status() == CaseStatus.FILED
    case._status = CaseStatus.CLOSED
    assert case.next_status() is None
    case._status = CaseStatus.CANCELLED
    assert case.next_status() is None
