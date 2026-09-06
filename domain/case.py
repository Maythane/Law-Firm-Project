"""BL-02: Case — สถานะและหมายเลขคดี

ดูขอบเขตงานเต็มที่ backlog.md#bl-02

หมายเลขคดีดำ/แดง (black_case_no/red_case_no) เก็บเป็นสตริงที่จัดรูปแบบไว้แล้ว
(เช่น "1234/2568") — การออกเลขจริงเป็นหน้าที่ของ LawFirm.open_case() (BL-11)
display_black_no()/display_red_no() แค่คืนค่าที่มีอยู่ หรือ "-" ถ้ายังไม่มี
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from domain.assignment import AssignmentStatus
from domain.errors import InvalidStatusTransition
from domain.person import Client, Lawyer


class CaseStatus(Enum):
    OPEN = "open"
    FILED = "filed"
    TRIAL = "trial"
    JUDGED = "judged"
    FINAL = "final"
    CLOSED = "closed"
    CANCELLED = "cancelled"


_ADVANCE_ORDER = [
    CaseStatus.OPEN,
    CaseStatus.FILED,
    CaseStatus.TRIAL,
    CaseStatus.JUDGED,
    CaseStatus.FINAL,
    CaseStatus.CLOSED,
]

_RED_NUMBER_ALLOWED_FROM = {CaseStatus.JUDGED, CaseStatus.FINAL, CaseStatus.CLOSED}


@dataclass
class Case:
    title: str
    client: Client
    client_role: str
    opposing_party: str
    court_name: str
    opened_date: date
    black_case_no: str | None = None
    red_case_no: str | None = None
    filed_date: date | None = None
    id: int | None = field(default=None, kw_only=True)
    _status: CaseStatus = field(default=CaseStatus.OPEN, kw_only=True)
    _status_before_cancel: CaseStatus | None = field(default=None, kw_only=True)
    _assignments: list["CaseAssignment"] = field(default_factory=list, kw_only=True)

    @property
    def status(self) -> CaseStatus:
        return self._status

    def lawyers(self) -> list[Lawyer]:
        """ทนายที่ ACCEPTED แล้วเท่านั้น — BL-14 + BL-24 (BR-15)"""
        return [a.lawyer for a in self._assignments if a.status == AssignmentStatus.ACCEPTED]

    def lead_lawyer(self) -> Lawyer | None:
        for a in self._assignments:
            if a.status == AssignmentStatus.ACCEPTED and a.is_lead:
                return a.lawyer
        return None

    def display_black_no(self) -> str:
        return self.black_case_no or "-"

    def display_red_no(self) -> str:
        return self.red_case_no or "-"

    def advance_status(self, new_status: CaseStatus) -> None:
        """เลื่อนได้ทีละขั้นเท่านั้น ข้ามขั้นแล้วโยน error — BR-7
        เข้าสถานะ FILED ต้องมีทนายตอบรับแล้วอย่างน้อย 1 คน — BR-18
        """
        if self._status == CaseStatus.CANCELLED:
            raise InvalidStatusTransition("คดีที่ยกเลิกแล้วเลื่อนสถานะต่อไม่ได้")
        current_index = _ADVANCE_ORDER.index(self._status)
        next_index = current_index + 1
        if next_index >= len(_ADVANCE_ORDER) or new_status != _ADVANCE_ORDER[next_index]:
            raise InvalidStatusTransition(
                f"เลื่อนสถานะจาก {self._status.value} ไป {new_status.value} ไม่ได้ "
                "ต้องเลื่อนทีละขั้น (BR-7)"
            )
        if new_status == CaseStatus.FILED and not self.lawyers():
            raise InvalidStatusTransition(
                "ยื่นฟ้องไม่ได้ ยังไม่มีทนายตอบรับคดีนี้เลย (BR-18)"
            )
        self._status = new_status

    def assign_red_number(self, red_case_no: str) -> None:
        """ออกเลขคดีแดงได้เฉพาะสถานะถึงตัดสินแล้ว — BR-8"""
        if self._status not in _RED_NUMBER_ALLOWED_FROM:
            raise InvalidStatusTransition(
                "ออกหมายเลขคดีแดงได้เฉพาะตอนสถานะถึงตัดสินแล้ว (BR-8)"
            )
        self.red_case_no = red_case_no

    def cancel(self, reason: str) -> None:
        """ยกเลิกได้จากทุกสถานะยกเว้นปิดคดี/ยกเลิกแล้ว บังคับมีเหตุผล"""
        if not reason or not reason.strip():
            raise ValueError("ต้องระบุเหตุผลที่ยกเลิกคดี")
        if self._status in (CaseStatus.CLOSED, CaseStatus.CANCELLED):
            raise InvalidStatusTransition("ยกเลิกคดีที่ปิดแล้วหรือยกเลิกไปแล้วไม่ได้")
        self._status_before_cancel = self._status
        self._status = CaseStatus.CANCELLED

    def reopen(self, reason: str) -> None:
        """กลับมาที่สถานะก่อนยกเลิก ไม่ใช่ย้อนไปเปิดคดีใหม่"""
        if not reason or not reason.strip():
            raise ValueError("ต้องระบุเหตุผลที่เปิดคดีคืน")
        if self._status != CaseStatus.CANCELLED:
            raise InvalidStatusTransition("เปิดคดีคืนได้เฉพาะคดีที่ถูกยกเลิกอยู่")
        self._status = self._status_before_cancel
        self._status_before_cancel = None

    def can_close(self, has_future_appointments: bool, has_pending_filing_deadlines: bool) -> bool:
        """เท็จถ้ายังมีนัดในอนาคตหรือกำหนดยื่นที่ยังไม่ทำ — BR-9"""
        return not (has_future_appointments or has_pending_filing_deadlines)
