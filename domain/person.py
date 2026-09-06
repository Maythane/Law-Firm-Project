"""BL-01: Person (abstract) -> Lawyer, Client
BL-23: SystemUser(Person) (abstract) -> Lawyer, Manager, Admin
       can_view_case(case)/dashboard_cards() ตอบคนละแบบ — สิทธิ์ทั้งระบบตรวจผ่านเมธอดนี้จุดเดียว ไม่มี if role==
ดูขอบเขตงานเต็มที่ backlog.md#bl-01, #bl-23

ponytail: username/password_hash เป็นสตริงว่างไปก่อน (placeholder) — BL-25 เป็นคนตัดสินวิธี hash จริง
check_password() ตามผังคลาสใน uml.md ก็รอ BL-25 เช่นกัน ยังไม่ใส่เพราะยังไม่มีวิธี hash ที่ตัดสินแล้ว
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Person(ABC):
    name: str
    citizen_id: str
    phone: str
    id: int | None = field(default=None, kw_only=True)

    @abstractmethod
    def display_name(self) -> str:
        ...

    def contact_info(self) -> str:
        return f"{self.name} ({self.phone})"


@dataclass
class SystemUser(Person):
    username: str = field(default="", kw_only=True)
    password_hash: str = field(default="", kw_only=True)
    is_active: bool = field(default=True, kw_only=True)

    @abstractmethod
    def can_view_case(self, case: "Case") -> bool:
        ...

    @abstractmethod
    def dashboard_cards(self) -> list[str]:
        ...


@dataclass
class Lawyer(SystemUser):
    license_no: str

    def display_name(self) -> str:
        return f"ทนาย{self.name}"

    def can_view_case(self, case: "Case") -> bool:
        """เฉพาะคดีที่ตนตอบรับแล้ว — BR-15 (case.lawyers() คืนเฉพาะ ACCEPTED ตั้งแต่ BL-24)"""
        return self in case.lawyers()

    def dashboard_cards(self) -> list[str]:
        return ["today_schedule", "upcoming_reminders", "my_cases", "pending_assignments"]

    def workload(self, cases: list["Case"], appointments: list["Appointment"]) -> int:
        """จำนวนคดีที่ตอบรับอยู่ + นัดในอีก 30 วัน — ใช้ในหน้ามอบหมาย

        ผู้เรียกกรอง cases/appointments ที่เกี่ยวข้องมาให้แล้ว (accepted cases, นัดใน 30 วันข้างหน้า)
        """
        return len(cases) + len(appointments)


@dataclass
class Manager(SystemUser):
    def display_name(self) -> str:
        return f"ผู้จัดการ{self.name}"

    def can_view_case(self, case: "Case") -> bool:
        return True

    def dashboard_cards(self) -> list[str]:
        return ["unassigned_cases", "recently_declined_assignments", "lawyer_workload"]


@dataclass
class Admin(SystemUser):
    def display_name(self) -> str:
        return f"ผู้ดูแลระบบ{self.name}"

    def can_view_case(self, case: "Case") -> bool:
        return False

    def dashboard_cards(self) -> list[str]:
        return ["user_management"]


@dataclass
class Client(Person):
    company: str | None = None

    def display_name(self) -> str:
        return self.company if self.company else self.name
