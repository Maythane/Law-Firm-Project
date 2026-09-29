"""BL-18: repository ของตาราง case_assignments"""

from domain.assignment import AssignmentStatus, CaseAssignment
from repository.case_repo import CaseRepository
from repository.user_repo import UserRepository


class AssignmentRepository:
    """ที่เก็บการมอบหมาย — ถือ connection ไว้หนึ่งตัว เมธอดชื่อเดิม (ตัดพารามิเตอร์ conn ตัวแรกออก)"""

    def __init__(self, conn, cases: CaseRepository | None = None, users: UserRepository | None = None):
        self._conn = conn
        self._cases = cases or CaseRepository(conn)
        self._users = users or UserRepository(conn)

    def _row_to_assignment(self, row: dict, case) -> CaseAssignment:
        return CaseAssignment(
            case=case,
            lawyer=self._users.get_by_id(row["lawyer_id"]),
            assigned_by=self._users.get_by_id(row["assigned_by"]),
            assigned_at=row["assigned_at"],
            is_lead=bool(row["is_lead"]),
            status=AssignmentStatus(row["status"]),
            responded_at=row["responded_at"],
            decline_reason=row["decline_reason"],
            withdraw_requested_at=row["withdraw_requested_at"],
            withdraw_reason_code=row["withdraw_reason_code"],
            withdraw_note=row["withdraw_note"],
            withdraw_reject_reason=row["withdraw_reject_reason"],
            id=row["id"],
        )

    def get_by_id(self, assignment_id: int) -> CaseAssignment | None:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM case_assignments WHERE id = %s", (assignment_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_assignment(row, self._cases.get_by_id(row["case_id"]))

    def list_for_case(self, case) -> list[CaseAssignment]:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM case_assignments WHERE case_id = %s", (case.id,))
        return [self._row_to_assignment(row, case) for row in cur.fetchall()]

    def list_pending_for_lawyer(self, lawyer_id: int) -> list[CaseAssignment]:
        """กล่องคดีรอการตอบรับบน dashboard ทนาย — BL-27"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM case_assignments WHERE lawyer_id = %s AND status = 'pending' ORDER BY assigned_at",
            (lawyer_id,),
        )
        rows = cur.fetchall()
        return [self._row_to_assignment(row, self._cases.get_by_id(row["case_id"])) for row in rows]

    def list_accepted_for_lawyer(self, lawyer_id: int) -> list[CaseAssignment]:
        """รายการ "คดีของฉัน" — คดีที่ตอบรับแล้ว (รวมที่ขอถอนตัวรออนุมัติ) พร้อมบทบาทหลัก/ร่วมในตัว assignment"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM case_assignments WHERE lawyer_id = %s AND status = 'accepted'", (lawyer_id,)
        )
        rows = cur.fetchall()
        return [self._row_to_assignment(row, self._cases.get_by_id(row["case_id"])) for row in rows]

    def list_pending_for_cases(self, cases) -> dict[int, list[CaseAssignment]]:
        """รายการรอตอบรับของแต่ละคดี (case.id -> [assignment เก่าสุดก่อน]) — แสดง "รอทนายใคร ตอบรับกี่วันแล้ว" ในกล่องแจ้งเตือน"""
        if not cases:
            return {}
        by_id = {c.id: c for c in cases}
        placeholders = ", ".join(["%s"] * len(by_id))
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            f"SELECT * FROM case_assignments WHERE status = 'pending' AND case_id IN ({placeholders}) "
            "ORDER BY assigned_at, id",
            tuple(by_id),
        )
        result: dict[int, list[CaseAssignment]] = {}
        for row in cur.fetchall():
            result.setdefault(row["case_id"], []).append(self._row_to_assignment(row, by_id[row["case_id"]]))
        return result

    def list_withdraw_requests(self) -> list[CaseAssignment]:
        """คำขอถอนตัวที่รออนุมัติ — กล่องบน dashboard manager + badge sidebar"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM case_assignments WHERE status = 'accepted' AND withdraw_requested_at IS NOT NULL "
            "ORDER BY withdraw_requested_at"
        )
        rows = cur.fetchall()
        return [self._row_to_assignment(row, self._cases.get_by_id(row["case_id"])) for row in rows]

    def list_unresolved_declined(self) -> list[CaseAssignment]:
        """คดีที่ทนายปฏิเสธและยัง "ค้าง" — ตอนนี้ไม่มีทนายตอบรับและไม่มีทนายรอตอบรับคนใหม่ (มอบหมายใหม่แล้วแถวนี้หายเอง)
        หน้าแรกของ manager (BL-26) · นับเป็นแถว (หนึ่งการปฏิเสธ = หนึ่งคำขอ) เรียงเก่าสุดก่อน
        """
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            """SELECT d.* FROM case_assignments d
               JOIN cases c ON c.id = d.case_id
               WHERE d.status = 'declined'
               AND c.status NOT IN ('closed', 'cancelled')
               AND NOT EXISTS (
                   SELECT 1 FROM case_assignments a
                   WHERE a.case_id = d.case_id AND a.status IN ('accepted', 'pending')
               )
               ORDER BY d.responded_at, d.id"""
        )
        rows = cur.fetchall()
        return [self._row_to_assignment(row, self._cases.get_by_id(row["case_id"])) for row in rows]

    def add(self, assignment: CaseAssignment) -> CaseAssignment:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO case_assignments
               (case_id, lawyer_id, assigned_by, assigned_at, status, responded_at,
                decline_reason, is_lead)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                assignment.case.id,
                assignment.lawyer.id,
                assignment.assigned_by.id,
                assignment.assigned_at,
                assignment.status.value,
                assignment.responded_at,
                assignment.decline_reason,
                assignment.is_lead,
            ),
        )
        self._conn.commit()
        assignment.id = cur.lastrowid
        return assignment

    def update_status(self, assignment: CaseAssignment) -> None:
        """เขียนสถานะปัจจุบัน (หลัง accept()/decline()/request_withdraw() ฯลฯ) ลง DB"""
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE case_assignments SET status = %s, responded_at = %s, decline_reason = %s, "
            "withdraw_requested_at = %s, withdraw_reason_code = %s, withdraw_note = %s, "
            "withdraw_reject_reason = %s WHERE id = %s",
            (
                assignment.status.value, assignment.responded_at, assignment.decline_reason,
                assignment.withdraw_requested_at, assignment.withdraw_reason_code,
                assignment.withdraw_note, assignment.withdraw_reject_reason, assignment.id,
            ),
        )
        self._conn.commit()
