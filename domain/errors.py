"""ตระกูล exception ของชั้น domain — ตัดสินไว้ใน backlog.md หัวข้อ 2 (6 ก.ย. 2569)

ชั้น FastAPI (api/) แมป DomainError -> HTTP 400 ที่ exception handler จุดเดียว
เทสต์ต้อง raise/assert ชนิด subclass ที่เจาะจง ไม่ใช่ DomainError เฉยๆ
"""


class DomainError(Exception):
    """แม่ของ error ทุกชนิดที่เกิดจากการละเมิดกฎธุรกิจ (BR-*)"""


class ScheduleConflictError(DomainError):
    """นัดใหม่ทับกับนัดเดิมของทนายคนเดียวกัน — BR-1"""


class InvalidStatusTransition(DomainError):
    """เปลี่ยนสถานะคดีข้ามขั้น หรือยังไม่ครบเงื่อนไข — BR-7, BR-8, BR-9, BR-18"""


class RescheduleNotAllowed(DomainError):
    """เลื่อนนัดที่เลื่อนไม่ได้ หรือเลื่อนโดยไม่มีเหตุผลกำกับ — BR-3, BR-5"""


class AssignmentError(DomainError):
    """action บน CaseAssignment ผิดสถานะ หรือมอบหมายซ้ำ หรือปฏิเสธโดยไม่มีเหตุผล — BR-15 ถึง BR-19"""
