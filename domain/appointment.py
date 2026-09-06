"""BL-03: Appointment (abstract) -> CourtHearing, ClientMeeting, FilingDeadline

BL-05 เพิ่ม FilingDeadline.from_event() ต่อจากนี้
BL-12 เพิ่มการเก็บประวัติการเลื่อนและ cancel() ต่อจากนี้ — reschedule() ที่นี่เป็นเวอร์ชันขั้นต่ำ
ดูขอบเขตงานเต็มที่ backlog.md#bl-03, #bl-05, #bl-12
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import ClassVar

from domain.case import Case
from domain.errors import RescheduleNotAllowed
from domain.person import Lawyer


@dataclass
class AppointmentChange:
    """แถวประวัติการเลื่อนนัดหนึ่งครั้ง — BL-12"""

    old_starts_at: datetime
    new_starts_at: datetime
    reason: str | None
    changed_at: datetime


@dataclass
class Appointment(ABC):
    case: Case
    lawyer: Lawyer
    starts_at: datetime
    ends_at: datetime
    location: str
    is_done: bool = field(default=False, kw_only=True)
    is_cancelled: bool = field(default=False, kw_only=True)
    cancel_reason: str | None = field(default=None, kw_only=True)
    reschedule_history: list[AppointmentChange] = field(default_factory=list, kw_only=True)
    id: int | None = field(default=None, kw_only=True)

    @abstractmethod
    def reminder_lead_days(self) -> int:
        ...

    @abstractmethod
    def can_reschedule(self, reason: str | None = None) -> bool:
        ...

    @abstractmethod
    def kind_label(self) -> str:
        ...

    def overlaps(self, other: "Appointment") -> bool:
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at

    def is_due_soon(self, today: date) -> bool:
        days_until = (self.starts_at.date() - today).days
        return days_until <= self.reminder_lead_days()

    def reschedule(self, new_starts_at: datetime, reason: str | None = None) -> None:
        """ย้ายเวลานัด — เก็บประวัติต่อท้ายทุกครั้ง ไม่ทับของเดิม (BL-12)"""
        if not self.can_reschedule(reason):
            raise RescheduleNotAllowed(f"{self.kind_label()} เลื่อนไม่ได้ในเงื่อนไขนี้")
        duration = self.ends_at - self.starts_at
        old_starts_at = self.starts_at
        self.starts_at = new_starts_at
        self.ends_at = new_starts_at + duration
        self.reschedule_history.append(
            AppointmentChange(
                old_starts_at=old_starts_at,
                new_starts_at=new_starts_at,
                reason=reason,
                changed_at=datetime.now(),
            )
        )

    def cancel(self, reason: str) -> None:
        """ทำเครื่องหมายยกเลิก ไม่ลบรายการทิ้ง — BL-12"""
        if not reason or not reason.strip():
            raise ValueError("ต้องระบุเหตุผลที่ยกเลิกนัด")
        self.is_cancelled = True
        self.cancel_reason = reason


@dataclass
class CourtHearing(Appointment):
    court_name: str
    room_no: str

    def reminder_lead_days(self) -> int:
        return 3

    def can_reschedule(self, reason: str | None = None) -> bool:
        """เลื่อนได้เฉพาะเมื่อมีเหตุผลกำกับ — BR-3"""
        return bool(reason and reason.strip())

    def kind_label(self) -> str:
        return "นัดศาล"


@dataclass
class ClientMeeting(Appointment):
    def reminder_lead_days(self) -> int:
        return 1

    def can_reschedule(self, reason: str | None = None) -> bool:
        return True

    def kind_label(self) -> str:
        return "นัดพบลูกความ"


@dataclass
class FilingDeadline(Appointment):
    triggered_by_event: str

    APPEAL_DEADLINE_DAYS: ClassVar[int] = 30  # อุทธรณ์ 30 วันนับจากวันอ่านคำพิพากษา

    def reminder_lead_days(self) -> int:
        return 15

    def can_reschedule(self, reason: str | None = None) -> bool:
        """เลื่อนไม่ได้เลย — BR-5"""
        return False

    def kind_label(self) -> str:
        return "กำหนดยื่นเอกสาร"

    @classmethod
    def from_event(
        cls,
        case: Case,
        lawyer: Lawyer,
        event_name: str,
        event_date: date,
        days: int,
        location: str = "-",
    ) -> "FilingDeadline":
        """คำนวณวันครบกำหนดจากวันเกิดเหตุการณ์ + จำนวนวัน — BL-05"""
        deadline_date = event_date + timedelta(days=days)
        return cls(
            case=case,
            lawyer=lawyer,
            starts_at=datetime.combine(deadline_date, time.min),
            ends_at=datetime.combine(deadline_date, time.max),
            location=location,
            triggered_by_event=event_name,
        )
