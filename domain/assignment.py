"""BL-24: CaseAssignment — มอบหมายทนายพร้อมสถานะรอตอบรับ/ตอบรับ/ปฏิเสธ

BR-15 ถึง BR-19 — ดูขอบเขตงานเต็มที่ backlog.md#bl-24
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from domain.errors import AssignmentError


class AssignmentStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


@dataclass
class CaseAssignment:
    case: "Case"
    lawyer: "Lawyer"
    assigned_by: "Manager"
    assigned_at: datetime
    is_lead: bool = field(default=False, kw_only=True)
    status: AssignmentStatus = field(default=AssignmentStatus.PENDING, kw_only=True)
    responded_at: datetime | None = field(default=None, kw_only=True)
    decline_reason: str | None = field(default=None, kw_only=True)
    id: int | None = field(default=None, kw_only=True)

    def is_pending(self) -> bool:
        return self.status == AssignmentStatus.PENDING

    def accept(self) -> None:
        """รับคดี — ทำได้เฉพาะตอนยังรอตอบรับอยู่ เรียกซ้ำหรือผิดสถานะโยน error"""
        if self.status != AssignmentStatus.PENDING:
            raise AssignmentError("รับคดีได้เฉพาะรายการที่ยังรอตอบรับอยู่เท่านั้น")
        self.status = AssignmentStatus.ACCEPTED
        self.responded_at = datetime.now()

    def decline(self, reason: str) -> None:
        """ปฏิเสธคดี — บังคับมีเหตุผล (BR-16) ทำได้เฉพาะตอนยังรอตอบรับอยู่"""
        if self.status != AssignmentStatus.PENDING:
            raise AssignmentError("ปฏิเสธได้เฉพาะรายการที่ยังรอตอบรับอยู่เท่านั้น")
        if not reason or not reason.strip():
            raise ValueError("ต้องระบุเหตุผลที่ปฏิเสธคดี")
        self.status = AssignmentStatus.DECLINED
        self.decline_reason = reason
        self.responded_at = datetime.now()
