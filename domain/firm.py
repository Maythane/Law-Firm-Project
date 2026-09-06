"""BL-11: LawFirm — เปิดคดีและค้นหา
BL-14/BL-24: assign_lawyer() — มอบหมายทนายเป็น CaseAssignment (รอตอบรับ/ตอบรับ/ปฏิเสธ)
             ปฏิเสธมอบหมายซ้ำที่ยัง PENDING/ACCEPTED — BR-17
ดูขอบเขตงานเต็มที่ backlog.md#bl-11, #bl-14, #bl-24

ponytail: การออกเลขคดีดำอัตโนมัติตอนยื่นฟ้อง (ที่กล่าวถึงใน backlog.md#bl-11) ยังไม่ทำ —
ไม่มีอยู่ใน "เสร็จเมื่อ" ของ BL-11 และไม่มีชื่อเมธอดระบุในผังคลาส (uml.md)
เพิ่มตอน BL-18/BL-20 ที่ต่อ UI ยื่นฟ้องจริงแล้วรู้ workflow ที่แน่ชัด

ponytail: search() ยังไม่ค้นชื่อทนาย — ไม่มีอยู่ใน "เสร็จเมื่อ" ของ BL-11 เช่นกัน
"""

from dataclasses import dataclass, field
from datetime import datetime

from domain.assignment import AssignmentStatus, CaseAssignment
from domain.case import Case
from domain.errors import AssignmentError
from domain.person import Lawyer, Manager


@dataclass
class LawFirm:
    cases: list[Case] = field(default_factory=list)

    def open_case(self, case: Case) -> Case:
        self.cases.append(case)
        return case

    def find_by_case_no(self, case_no: str) -> Case | None:
        for case in self.cases:
            if case.black_case_no == case_no or case.red_case_no == case_no:
                return case
        return None

    def search(self, keyword: str) -> list[Case]:
        by_no = self.find_by_case_no(keyword)
        if by_no is not None:
            return [by_no]
        needle = keyword.lower()
        return [
            case
            for case in self.cases
            if needle in case.title.lower()
            or needle in case.client.name.lower()
            or needle in case.opposing_party.lower()
        ]

    def assign_lawyer(
        self, case: Case, lawyer: Lawyer, assigned_by: Manager, *, is_lead: bool = False
    ) -> CaseAssignment:
        """มอบหมายทนายให้คดี เป็นรายการรอตอบรับ — ปฏิเสธมอบหมายซ้ำที่ยัง PENDING/ACCEPTED (BR-17)"""
        for existing in case._assignments:
            if existing.lawyer == lawyer and existing.status in (
                AssignmentStatus.PENDING,
                AssignmentStatus.ACCEPTED,
            ):
                raise AssignmentError(
                    f"{lawyer.display_name()} มีการมอบหมายคดีนี้ค้างอยู่แล้ว (BR-17)"
                )
        assignment = CaseAssignment(
            case=case,
            lawyer=lawyer,
            assigned_by=assigned_by,
            assigned_at=datetime.now(),
            is_lead=is_lead,
        )
        case._assignments.append(assignment)
        return assignment
