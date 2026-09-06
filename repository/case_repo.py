"""BL-18: repository ของตาราง cases — find_by_case_no ค้นทั้งเลขคดีดำและคดีแดง

หมายเหตุ: get_by_id()/find_by_case_no() คืน Case ที่ _assignments ยังว่างอยู่
เรียก assignment_repo.list_for_case() แล้ว extend เข้า case._assignments เอง ถ้าต้องใช้ lawyers()/lead_lawyer()
"""

from domain.case import Case, CaseStatus
from repository.client_repo import get_by_id as get_client_by_id


def _row_to_case(conn, row: dict) -> Case:
    client = get_client_by_id(conn, row["client_id"])
    case = Case(
        title=row["title"],
        client=client,
        client_role=row["client_role"],
        opposing_party=row["opposing_party"],
        court_name=row["court_name"],
        opened_date=row["opened_date"],
        black_case_no=row["black_case_no"],
        red_case_no=row["red_case_no"],
        filed_date=row["filed_date"],
        id=row["id"],
    )
    # ตั้ง _status ตรงๆ แทนการเรียก advance_status() เพราะแค่ประกอบข้อมูลเดิมจาก DB ไม่ใช่การเปลี่ยนสถานะจริง
    case._status = CaseStatus(row["status"])
    return case


def get_by_id(conn, case_id: int) -> Case | None:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
    row = cur.fetchone()
    return _row_to_case(conn, row) if row else None


def find_by_case_no(conn, case_no: str) -> Case | None:
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM cases WHERE black_case_no = %s OR red_case_no = %s", (case_no, case_no)
    )
    row = cur.fetchone()
    return _row_to_case(conn, row) if row else None


def list_accepted_by_lawyer(conn, lawyer_id: int) -> list[Case]:
    """คดีที่ทนายคนนี้ตอบรับแล้ว — ใช้เลือกคดีตอนสร้างนัดใหม่ (BL-20)"""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT DISTINCT c.* FROM cases c
           JOIN case_assignments a ON a.case_id = c.id
           WHERE a.lawyer_id = %s AND a.status = 'accepted'
           ORDER BY c.title""",
        (lawyer_id,),
    )
    return [_row_to_case(conn, row) for row in cur.fetchall()]


def list_without_accepted_lawyer(conn) -> list[Case]:
    """คดีที่ยังไม่มีทนายตอบรับ ไม่รวมคดีที่ปิด/ยกเลิกแล้ว — หน้าแรกของ manager (BL-26)"""
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT c.* FROM cases c
           WHERE c.status NOT IN ('closed', 'cancelled')
           AND NOT EXISTS (
               SELECT 1 FROM case_assignments a WHERE a.case_id = c.id AND a.status = 'accepted'
           )
           ORDER BY c.opened_date"""
    )
    return [_row_to_case(conn, row) for row in cur.fetchall()]


def add(conn, case: Case) -> Case:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO cases
           (title, black_case_no, red_case_no, client_id, client_role, opposing_party,
            court_name, status, opened_date, filed_date)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            case.title,
            case.black_case_no,
            case.red_case_no,
            case.client.id,
            case.client_role,
            case.opposing_party,
            case.court_name,
            case.status.value,
            case.opened_date,
            case.filed_date,
        ),
    )
    conn.commit()
    case.id = cur.lastrowid
    return case
