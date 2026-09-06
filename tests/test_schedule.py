# BL-16 (tests/test_schedule.py) รวมกฎทุกอย่างของนัดหมาย/คดีไว้ที่นี่ตามที่ backlog.md#bl-16 ระบุ
# ตอนนี้มีเฉพาะส่วนของ BL-04 (Schedule) — เพิ่มการยืนยัน from_event()/advance_status()/assign_red_number()
# เมื่อ BL-05, BL-06 เสร็จ แล้วค่อยติ๊ก BL-16 ว่าเสร็จ

from datetime import date, datetime

import pytest

from domain.appointment import ClientMeeting, CourtHearing, FilingDeadline
from domain.assignment import AssignmentStatus, CaseAssignment
from domain.case import Case
from domain.errors import ScheduleConflictError
from domain.person import Client, Lawyer
from domain.schedule import Schedule


def make_case():
    return Case(
        title="ผิดสัญญาซื้อขาย",
        client=Client(name="สมหญิง", citizen_id="2", phone="081"),
        client_role="โจทก์",
        opposing_party="บจก. คู่กรณี",
        court_name="ศาลแพ่งกรุงเทพใต้",
        opened_date=date(2026, 1, 1),
    )


def make_lawyer(citizen_id="1"):
    return Lawyer(name="สมชาย", citizen_id=citizen_id, phone="080", license_no="L1")


def ensure_accepted(case, lawyer):
    """schedule.add() ปฏิเสธนัดของทนายที่ยังไม่ตอบรับคดี (BR-19) — เทสนี้ไม่ได้สนใจ workflow
    ตอบรับ/ปฏิเสธเอง (นั่นคือ BL-24/test_assignment.py) จึงตั้งให้ตอบรับแล้วตรงๆ
    """
    if lawyer not in case.lawyers():
        case._assignments.append(
            CaseAssignment(
                case=case, lawyer=lawyer, assigned_by=None, assigned_at=datetime.now(),
                status=AssignmentStatus.ACCEPTED,
            )
        )


def meeting(case, lawyer, start_hour, end_hour, day=10):
    ensure_accepted(case, lawyer)
    return ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, day, start_hour, 0),
        ends_at=datetime(2026, 3, day, end_hour, 0),
        location="สำนักงาน",
    )


def test_add_rejects_overlapping_appointment_of_same_lawyer():
    case, lawyer = make_case(), make_lawyer()
    schedule = Schedule()
    schedule.add(meeting(case, lawyer, 9, 10))
    overlapping = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 30), ends_at=datetime(2026, 3, 10, 10, 30),
        location="สำนักงาน",
    )

    with pytest.raises(ScheduleConflictError):
        schedule.add(overlapping)


def test_add_allows_same_time_for_different_lawyer():
    case = make_case()
    lawyer_a, lawyer_b = make_lawyer("1"), make_lawyer("2")
    schedule = Schedule()
    schedule.add(meeting(case, lawyer_a, 9, 10))
    schedule.add(meeting(case, lawyer_b, 9, 10))  # คนละทนาย เวลาเดียวกัน ต้องเพิ่มได้

    assert len(schedule.appointments) == 2


def test_add_allows_back_to_back_appointments():
    case, lawyer = make_case(), make_lawyer()
    schedule = Schedule()
    schedule.add(meeting(case, lawyer, 9, 10))
    schedule.add(meeting(case, lawyer, 10, 11))  # จบ 10:00 เริ่ม 10:00 ไม่ถือว่าชน

    assert len(schedule.appointments) == 2


def test_day_view_sorted_by_start_time_and_filtered_by_lawyer():
    case = make_case()
    lawyer_a, lawyer_b = make_lawyer("1"), make_lawyer("2")
    schedule = Schedule()
    later = meeting(case, lawyer_a, 14, 15)
    earlier = meeting(case, lawyer_a, 9, 10)
    other_lawyer = meeting(case, lawyer_b, 8, 9)
    schedule.add(later)
    schedule.add(earlier)
    schedule.add(other_lawyer)

    result = schedule.day_view(lawyer_a, date(2026, 3, 10))

    assert result == [earlier, later]


def test_week_view_filters_by_lawyer_and_date_range():
    case, lawyer = make_case(), make_lawyer()
    schedule = Schedule()
    in_week = meeting(case, lawyer, 9, 10, day=12)
    out_of_week = meeting(case, lawyer, 9, 10, day=20)
    schedule.add(in_week)
    schedule.add(out_of_week)

    result = schedule.week_view(lawyer, week_start=date(2026, 3, 9))

    assert result == [in_week]


def test_upcoming_reminders_combines_all_kinds_sorted_by_urgency():
    case, lawyer = make_case(), make_lawyer()
    today = date(2026, 3, 1)
    schedule = Schedule()
    hearing = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 3), ends_at=datetime(2026, 3, 3),
        location="ศาล", court_name="c", room_no="1",
    )  # 2 วัน, lead 3 -> due
    deadline = FilingDeadline(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10), ends_at=datetime(2026, 3, 10),
        location="-", triggered_by_event="x",
    )  # 9 วัน, lead 15 -> due
    not_due_meeting = meeting(case, lawyer, 9, 10)  # 9 วัน, lead 1 -> ไม่ due
    schedule.appointments.extend([deadline, hearing, not_due_meeting])

    result = schedule.upcoming_reminders(lawyer, today)

    assert result == [hearing, deadline]


def test_mark_done_removes_from_upcoming_reminders_but_keeps_in_schedule():
    case, lawyer = make_case(), make_lawyer()
    today = date(2026, 3, 1)
    schedule = Schedule()
    hearing = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 3), ends_at=datetime(2026, 3, 3),
        location="ศาล", court_name="c", room_no="1",
    )
    schedule.appointments.append(hearing)

    schedule.mark_done(hearing)

    assert schedule.upcoming_reminders(lawyer, today) == []
    assert hearing in schedule.appointments


def test_cancelled_appointment_excluded_from_views_but_kept_in_schedule():
    case, lawyer = make_case(), make_lawyer()
    schedule = Schedule()
    appt = meeting(case, lawyer, 9, 10)
    schedule.add(appt)

    appt.cancel("ลูกความยกเลิกนัด")

    assert schedule.day_view(lawyer, date(2026, 3, 10)) == []
    assert schedule.week_view(lawyer, week_start=date(2026, 3, 9)) == []
    assert appt in schedule.appointments  # ยังอยู่ในประวัติคดี ไม่ถูกลบทิ้ง


def test_filing_deadline_does_not_count_as_conflict_or_conflict_with_others():
    # ตัดสินไว้ใน backlog.md: FilingDeadline เป็นรายการทั้งวัน ไม่เข้าการตรวจนัดชน
    case, lawyer = make_case(), make_lawyer()
    ensure_accepted(case, lawyer)
    schedule = Schedule()
    deadline = FilingDeadline(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 0, 0), ends_at=datetime(2026, 3, 10, 23, 59),
        location="-", triggered_by_event="x",
    )
    schedule.add(deadline)

    # นัดศาลเวลาปกติวันเดียวกัน ต้องเพิ่มได้ ไม่ถือว่าชนกับกำหนดยื่นที่ครอบทั้งวัน
    hearing = CourtHearing(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 3, 10, 9, 0), ends_at=datetime(2026, 3, 10, 10, 0),
        location="ศาล", court_name="c", room_no="1",
    )
    schedule.add(hearing)

    assert deadline in schedule.appointments
    assert hearing in schedule.appointments


def test_month_view_groups_appointments_by_day():
    case, lawyer = make_case(), make_lawyer()
    schedule = Schedule()
    a1 = meeting(case, lawyer, 9, 10, day=5)
    a2 = meeting(case, lawyer, 14, 15, day=5)
    a3 = meeting(case, lawyer, 9, 10, day=12)
    schedule.appointments.extend([a1, a2, a3])

    result = schedule.month_view(lawyer, 2026, 3)

    assert result[date(2026, 3, 5)] == [a1, a2]
    assert result[date(2026, 3, 12)] == [a3]
    assert date(2026, 3, 20) not in result


def test_month_view_excludes_other_lawyer_cancelled_and_other_months():
    case, lawyer = make_case(), make_lawyer()
    other_lawyer = make_lawyer("99")
    schedule = Schedule()
    mine = meeting(case, lawyer, 9, 10, day=5)
    other = meeting(case, other_lawyer, 9, 10, day=5)
    cancelled = meeting(case, lawyer, 9, 10, day=6)
    cancelled.cancel("ยกเลิกนัด")
    next_month = ClientMeeting(
        case=case, lawyer=lawyer,
        starts_at=datetime(2026, 4, 1, 9, 0), ends_at=datetime(2026, 4, 1, 10, 0),
        location="สำนักงาน",
    )
    schedule.appointments.extend([mine, other, cancelled, next_month])

    result = schedule.month_view(lawyer, 2026, 3)

    assert result[date(2026, 3, 5)] == [mine]
    assert date(2026, 3, 6) not in result
    assert date(2026, 4, 1) not in result


def test_cancelled_appointment_does_not_count_as_conflict():
    case, lawyer = make_case(), make_lawyer()
    schedule = Schedule()
    first = meeting(case, lawyer, 9, 10)
    schedule.add(first)
    first.cancel("ลูกความยกเลิกนัด")

    overlapping = meeting(case, lawyer, 9, 10)
    schedule.add(overlapping)  # ต้องเพิ่มได้ เพราะนัดเดิมยกเลิกไปแล้ว

    assert overlapping in schedule.appointments
