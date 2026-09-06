from datetime import date, datetime

import pytest

from domain.appointment import ClientMeeting, CourtHearing, FilingDeadline
from domain.case import Case
from domain.errors import RescheduleNotAllowed
from domain.person import Client, Lawyer


def make_case():
    return Case(
        title="ผิดสัญญาซื้อขาย",
        client=Client(name="สมหญิง", citizen_id="2", phone="081"),
        client_role="โจทก์",
        opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่งกรุงเทพใต้",
        opened_date=date(2026, 1, 1),
    )


def make_lawyer():
    return Lawyer(name="สมชาย", citizen_id="1", phone="080", license_no="L1")


def test_reminder_lead_days_differ_by_kind():
    case, lawyer = make_case(), make_lawyer()
    hearing = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="ศาล", court_name="ศาลแพ่ง", room_no="401",
    )
    meeting = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="สำนักงาน",
    )
    deadline = FilingDeadline(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 0, 0), ends_at=datetime(2026, 3, 10, 23, 59),
        location="-", triggered_by_event="อ่านคำพิพากษา",
    )

    assert hearing.reminder_lead_days() == 3
    assert meeting.reminder_lead_days() == 1
    assert deadline.reminder_lead_days() == 15


def test_is_due_soon_differs_by_kind_on_same_day():
    case, lawyer = make_case(), make_lawyer()
    today = date(2026, 3, 1)

    hearing_soon = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 3), ends_at=datetime(2026, 3, 3),
        location="x", court_name="c", room_no="1",
    )  # 2 วันจากนี้ -> due (lead 3)
    hearing_far = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10), ends_at=datetime(2026, 3, 10),
        location="x", court_name="c", room_no="1",
    )  # 9 วัน -> ไม่ due
    meeting_not_yet = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 3), ends_at=datetime(2026, 3, 3),
        location="x",
    )  # 2 วัน -> ไม่ due (lead 1)
    deadline_far = FilingDeadline(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10), ends_at=datetime(2026, 3, 10),
        location="x", triggered_by_event="x",
    )  # 9 วัน -> due (lead 15)

    assert hearing_soon.is_due_soon(today) is True
    assert hearing_far.is_due_soon(today) is False
    assert meeting_not_yet.is_due_soon(today) is False
    assert deadline_far.is_due_soon(today) is True


def test_court_hearing_requires_reason_to_reschedule():
    case, lawyer = make_case(), make_lawyer()
    hearing = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="ศาล", court_name="ศาลแพ่ง", room_no="401",
    )
    with pytest.raises(RescheduleNotAllowed):
        hearing.reschedule(datetime(2026, 3, 11, 9, 0))

    hearing.reschedule(datetime(2026, 3, 11, 9, 0), reason="ทนายติดว่าความคดีอื่น")
    assert hearing.starts_at == datetime(2026, 3, 11, 9, 0)
    assert hearing.ends_at == datetime(2026, 3, 11, 10, 0)


def test_client_meeting_reschedules_freely():
    case, lawyer = make_case(), make_lawyer()
    meeting = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="สำนักงาน",
    )
    meeting.reschedule(datetime(2026, 3, 12, 13, 0))
    assert meeting.starts_at == datetime(2026, 3, 12, 13, 0)


def test_filing_deadline_reschedule_always_raises():
    case, lawyer = make_case(), make_lawyer()
    deadline = FilingDeadline(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 0, 0), ends_at=datetime(2026, 3, 10, 23, 59),
        location="-", triggered_by_event="อ่านคำพิพากษา",
    )
    with pytest.raises(RescheduleNotAllowed):
        deadline.reschedule(datetime(2026, 3, 20, 0, 0), reason="เหตุผลใดก็ตาม")


def test_overlaps_true_for_overlapping_times():
    case, lawyer = make_case(), make_lawyer()
    a = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="x",
    )
    b = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 30), ends_at=datetime(2026, 3, 10, 10, 30),
        location="x",
    )
    assert a.overlaps(b) is True


def test_filing_deadline_from_event_computes_deadline_date():
    case, lawyer = make_case(), make_lawyer()
    judgment_date = date(2026, 3, 1)

    deadline = FilingDeadline.from_event(
        case=case,
        lawyer=lawyer,
        event_name="อ่านคำพิพากษา",
        event_date=judgment_date,
        days=FilingDeadline.APPEAL_DEADLINE_DAYS,
    )

    assert deadline.starts_at.date() == date(2026, 3, 31)  # 30 วันจาก 1 มี.ค.
    assert deadline.triggered_by_event == "อ่านคำพิพากษา"


def test_reschedule_three_times_keeps_full_history():
    case, lawyer = make_case(), make_lawyer()
    meeting = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="สำนักงาน",
    )

    meeting.reschedule(datetime(2026, 3, 11, 9, 0), reason="ลูกความติดธุระ")
    meeting.reschedule(datetime(2026, 3, 12, 9, 0), reason="ทนายติดศาลอื่น")
    meeting.reschedule(datetime(2026, 3, 13, 9, 0), reason="เลื่อนตามคำขอลูกความ")

    assert len(meeting.reschedule_history) == 3
    assert meeting.reschedule_history[0].old_starts_at == datetime(2026, 3, 10, 9, 0)
    assert meeting.reschedule_history[0].new_starts_at == datetime(2026, 3, 11, 9, 0)
    assert meeting.reschedule_history[0].reason == "ลูกความติดธุระ"
    assert meeting.reschedule_history[2].new_starts_at == datetime(2026, 3, 13, 9, 0)


def test_cancel_requires_reason_and_marks_cancelled():
    case, lawyer = make_case(), make_lawyer()
    meeting = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="สำนักงาน",
    )

    with pytest.raises(ValueError):
        meeting.cancel("")

    meeting.cancel("ลูกความยกเลิกนัด")
    assert meeting.is_cancelled is True
    assert meeting.cancel_reason == "ลูกความยกเลิกนัด"


def test_overlaps_false_when_back_to_back():
    case, lawyer = make_case(), make_lawyer()
    a = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="x",
    )
    b = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 10, 0), ends_at=datetime(2026, 3, 10, 11, 0),
        location="x",
    )
    assert a.overlaps(b) is False
