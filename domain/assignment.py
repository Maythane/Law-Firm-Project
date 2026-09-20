"""BL-24: CaseAssignment — มอบหมายทนายพร้อมสถานะรอตอบรับ/ตอบรับ/ปฏิเสธ

BR-15 ถึง BR-19 — ดูขอบเขตงานเต็มที่ backlog.md#bl-24
ขอถอนตัว (ทนายเปลี่ยนกะทันหัน) — ทนายที่ตอบรับแล้วขอ, manager อนุมัติ/ปฏิเสธ

ponytail: สถานะ "ขอถอนตัว รออนุมัติ" เป็น flag (withdraw_requested_at) บนแถว ACCEPTED ไม่ใช่ค่า enum ใหม่ —
ระหว่างรอ ทนายยังเป็นทนายของคดีเต็มตัว (Case.lawyers(), can_view_case(), workload ใช้ ACCEPTED เหมือนเดิมไม่ต้องแก้)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from domain.errors import AssignmentError


class AssignmentStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"  # manager อนุมัติคำขอถอนตัวแล้ว


WITHDRAW_REASONS = {
    "overload": "ภาระงานเกินเกณฑ์",
    "deadline": "ไม่ทันตามกำหนด",
    "other": "ไม่ไหว-ติดขัดอื่น",
}


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
    withdraw_requested_at: datetime | None = field(default=None, kw_only=True)
    withdraw_reason_code: str | None = field(default=None, kw_only=True)
    withdraw_note: str | None = field(default=None, kw_only=True)
    withdraw_reject_reason: str | None = field(default=None, kw_only=True)
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

    def is_withdraw_requested(self) -> bool:
        return self.status == AssignmentStatus.ACCEPTED and self.withdraw_requested_at is not None

    def request_withdraw(self, reason_code: str, note: str = "") -> None:
        """ขอถอนตัวจากคดี — เฉพาะทนายที่ตอบรับแล้ว ขอซ้ำระหว่างรออนุมัติไม่ได้ คดีปิด/ยกเลิกแล้วไม่ต้องขอ
        เหตุผลต้องเลือกจากรายการ และต้องมีรายละเอียดเมื่อเลือก "ไม่ไหว-ติดขัดอื่น"
        """
        if self.status != AssignmentStatus.ACCEPTED:
            raise AssignmentError("ขอถอนตัวได้เฉพาะคดีที่ตอบรับแล้วเท่านั้น")
        if self.withdraw_requested_at is not None:
            raise AssignmentError("มีคำขอถอนตัวรออนุมัติอยู่แล้ว")
        if self.case.status.value in ('closed', 'cancelled'):  # ไม่ import CaseStatus: case.py import ไฟล์นี้อยู่แล้ว (circular)
            raise AssignmentError("คดีที่ปิดหรือยกเลิกแล้วขอถอนตัวไม่ได้")
        if reason_code not in WITHDRAW_REASONS:
            raise ValueError("ต้องเลือกเหตุผลที่ขอถอนตัว")
        if reason_code == "other" and not note.strip():
            raise ValueError("ต้องระบุรายละเอียดเมื่อเลือก 'ไม่ไหว-ติดขัดอื่น'")
        self.withdraw_reason_code = reason_code
        self.withdraw_note = note.strip() or None
        self.withdraw_requested_at = datetime.now()
        self.withdraw_reject_reason = None

    def approve_withdraw(self) -> None:
        if not self.is_withdraw_requested():
            raise AssignmentError("ไม่มีคำขอถอนตัวที่รออนุมัติ")
        self.status = AssignmentStatus.WITHDRAWN

    def reject_withdraw(self, reason: str) -> None:
        """ปฏิเสธคำขอ — บังคับมีเหตุผล ทนายเดิมถือคดีต่อและเห็นเหตุผลนี้"""
        if not self.is_withdraw_requested():
            raise AssignmentError("ไม่มีคำขอถอนตัวที่รออนุมัติ")
        if not reason or not reason.strip():
            raise ValueError("ต้องระบุเหตุผลที่ไม่อนุมัติ")
        self.withdraw_requested_at = None
        self.withdraw_reject_reason = reason.strip()
