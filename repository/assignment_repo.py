"""BL-18: repository ของตาราง case_assignments"""

from domain.assignment import AssignmentStatus, CaseAssignment
from repository import case_repo
from repository.user_repo import get_by_id as get_user_by_id


def _row_to_assignment(conn, row: dict, case) -> CaseAssignment:
    return CaseAssignment(
        case=case,
        lawyer=get_user_by_id(conn, row["lawyer_id"]),
        assigned_by=get_user_by_id(conn, row["assigned_by"]),
        assigned_at=row["assigned_at"],
        is_lead=bool(row["is_lead"]),
        status=AssignmentStatus(row["status"]),
        responded_at=row["responded_at"],
        decline_reason=row["decline_reason"],
        id=row["id"],
    )


def get_by_id(conn, assignment_id: int) -> CaseAssignment | None:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM case_assignments WHERE id = %s", (assignment_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_assignment(conn, row, case_repo.get_by_id(conn, row["case_id"]))


def list_for_case(conn, case) -> list[CaseAssignment]:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM case_assignments WHERE case_id = %s", (case.id,))
    return [_row_to_assignment(conn, row, case) for row in cur.fetchall()]


def list_pending_for_lawyer(conn, lawyer_id: int) -> list[CaseAssignment]:
    """กล่องคดีรอการตอบรับบน dashboard ทนาย — BL-27"""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM case_assignments WHERE lawyer_id = %s AND status = 'pending' ORDER BY assigned_at",
        (lawyer_id,),
    )
    rows = cur.fetchall()
    return [_row_to_assignment(conn, row, case_repo.get_by_id(conn, row["case_id"])) for row in rows]


def list_recently_declined(conn, limit: int = 20) -> list[CaseAssignment]:
    """คดีที่เพิ่งถูกปฏิเสธพร้อมเหตุผล — หน้าแรกของ manager (BL-26)"""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM case_assignments WHERE status = 'declined' ORDER BY responded_at DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    return [_row_to_assignment(conn, row, case_repo.get_by_id(conn, row["case_id"])) for row in rows]


def add(conn, assignment: CaseAssignment) -> CaseAssignment:
    cur = conn.cursor()
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
    conn.commit()
    assignment.id = cur.lastrowid
    return assignment


def update_status(conn, assignment: CaseAssignment) -> None:
    """เขียนสถานะปัจจุบัน (หลัง accept()/decline()) ลง DB"""
    cur = conn.cursor()
    cur.execute(
        "UPDATE case_assignments SET status = %s, responded_at = %s, decline_reason = %s "
        "WHERE id = %s",
        (assignment.status.value, assignment.responded_at, assignment.decline_reason, assignment.id),
    )
    conn.commit()
