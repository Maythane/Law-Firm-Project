"""BL-04: Schedule — ตารางนัดและการตรวจนัดชน
BR-19 (ปฏิเสธนัดของทนายที่ยังไม่ตอบรับคดีนั้น) — BL-24
การกรองนัดที่ยกเลิกแล้วออกจากทุกมุมมอง — BL-12
BL-06 เพิ่ม upcoming_reminders()/mark_done() · BL-28 เพิ่ม month_view()
ดูขอบเขตงานเต็มที่ backlog.md#bl-04, #bl-28
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from domain.appointment import Appointment, FilingDeadline
from domain.errors import AssignmentError, ScheduleConflictError
from domain.person import Lawyer


@dataclass
class Schedule:
    appointments: list[Appointment] = field(default_factory=list)

    def find_conflicts(self, appt: Appointment) -> list[Appointment]:
        """เทียบเฉพาะนัดของทนายคนเดียวกัน ใช้ overlaps() — BR-1 ไม่มีกฎเวลาเดินทาง
        นัดที่ยกเลิกแล้วไม่ถูกนับเป็นนัดชน (BL-12)
        FilingDeadline เป็นรายการทั้งวัน ไม่เข้าการตรวจนัดชนทั้งสองทาง (ตัดสินไว้ใน backlog.md)
        """
        if isinstance(appt, FilingDeadline):
            return []
        return [
            existing
            for existing in self.appointments
            if existing is not appt
            and not existing.is_cancelled
            and not isinstance(existing, FilingDeadline)
            and existing.lawyer == appt.lawyer
            and existing.overlaps(appt)
        ]

    def add(self, appt: Appointment) -> None:
        if appt.lawyer not in appt.case.lawyers():
            raise AssignmentError(
                f"{appt.lawyer.display_name()} ยังไม่ตอบรับคดีนี้ สร้างนัดไม่ได้ (BR-19)"
            )
        conflicts = self.find_conflicts(appt)
        if conflicts:
            conflict = conflicts[0]
            raise ScheduleConflictError(
                f"นัดชนกับ{conflict.kind_label()}เวลา {conflict.starts_at} ของทนายคนเดียวกัน (BR-1)"
            )
        self.appointments.append(appt)

    def day_view(self, lawyer: Lawyer, day: date) -> list[Appointment]:
        items = [
            a
            for a in self.appointments
            if a.lawyer == lawyer and not a.is_cancelled and a.starts_at.date() == day
        ]
        return sorted(items, key=lambda a: a.starts_at)

    def week_view(self, lawyer: Lawyer, week_start: date) -> list[Appointment]:
        week_end = week_start + timedelta(days=6)
        items = [
            a
            for a in self.appointments
            if a.lawyer == lawyer
            and not a.is_cancelled
            and week_start <= a.starts_at.date() <= week_end
        ]
        return sorted(items, key=lambda a: a.starts_at)

    def upcoming_reminders(self, lawyer: Lawyer, today: date) -> list[Appointment]:
        """รวมนัดทุกชนิดที่ใกล้ครบกำหนดของทนายคนหนึ่ง เรียงจากเร่งด่วนที่สุด — FR-B3, FR-B4"""
        items = [
            a
            for a in self.appointments
            if a.lawyer == lawyer
            and not a.is_done
            and not a.is_cancelled
            and a.is_due_soon(today)
        ]
        return sorted(items, key=lambda a: a.starts_at)

    def mark_done(self, appt: Appointment) -> None:
        """หายจากหน้าเตือนแต่ยังอยู่ในประวัติของคดี — FR-B4"""
        appt.is_done = True

    def month_view(self, lawyer: Lawyer, year: int, month: int) -> dict[date, list[Appointment]]:
        """จัดกลุ่มนัดของทนายคนหนึ่งตามวันในเดือนที่ระบุ — FR-A2, FR-A5"""
        result: dict[date, list[Appointment]] = {}
        for a in self.appointments:
            if a.lawyer != lawyer or a.is_cancelled:
                continue
            day = a.starts_at.date()
            if day.year == year and day.month == month:
                result.setdefault(day, []).append(a)
        for items in result.values():
            items.sort(key=lambda a: a.starts_at)
        return result
