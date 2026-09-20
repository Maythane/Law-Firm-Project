"""BL-18: repository ของตาราง cases — find_by_case_no ค้นทั้งเลขคดีดำและคดีแดง

หมายเหตุ: get_by_id()/find_by_case_no() คืน Case ที่ _assignments ยังว่างอยู่
เรียก assignment_repo.list_for_case() แล้ว extend เข้า case._assignments เอง ถ้าต้องใช้ lawyers()/lead_lawyer()
"""

from datetime import datetime

from domain.case import Case, CaseEvent, CaseNote, CaseStatus
from repository.client_repo import get_by_id as get_client_by_id
from repository.user_repo import get_by_id as get_user_by_id


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
    """คดีที่ยังไม่มีทนายตอบรับและยังไม่มีทนายรอตอบรับ ไม่รวมคดีที่ปิด/ยกเลิกแล้ว — กล่องแจ้งเตือนของ manager (BL-26)
    มอบหมายทนายแล้ว (pending) คดีหายจากรายการนี้ทันที เพราะงานของ manager จบที่การมอบหมาย
    """
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT c.* FROM cases c
           WHERE c.status NOT IN ('closed', 'cancelled')
           AND NOT EXISTS (
               SELECT 1 FROM case_assignments a
               WHERE a.case_id = c.id AND a.status IN ('accepted', 'pending')
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


def update_progress(conn, case: Case) -> None:
    """เขียนสถานะและเลขคดีดำ/แดงปัจจุบันลง DB — เลขซ้ำกับคดีอื่นโยน mysql.connector.IntegrityError (UNIQUE)"""
    cur = conn.cursor()
    cur.execute(
        "UPDATE cases SET status = %s, black_case_no = %s, red_case_no = %s WHERE id = %s",
        (case.status.value, case.black_case_no, case.red_case_no, case.id),
    )
    conn.commit()


def add_note(conn, note: CaseNote) -> CaseNote:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO case_notes (case_id, author_id, text, created_at) VALUES (%s, %s, %s, %s)",
        (note.case_id, note.author.id, note.text, note.created_at),
    )
    conn.commit()
    note.id = cur.lastrowid
    return note


def get_note(conn, note_id: int) -> CaseNote | None:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM case_notes WHERE id = %s", (note_id,))
    row = cur.fetchone()
    return _row_to_note(conn, row) if row else None


def list_notes(conn, case_id: int) -> list[CaseNote]:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM case_notes WHERE case_id = %s ORDER BY created_at DESC, id DESC", (case_id,))
    return [_row_to_note(conn, row) for row in cur.fetchall()]


def _row_to_note(conn, row: dict) -> CaseNote:
    return CaseNote(
        case_id=row["case_id"], author=get_user_by_id(conn, row["author_id"]),
        text=row["text"], created_at=row["created_at"], id=row["id"],
    )


def update_note(conn, note: CaseNote) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE case_notes SET text = %s WHERE id = %s", (note.text, note.id))
    conn.commit()


def delete_note(conn, note_id: int) -> None:
    """ลบจริง ไม่ลง timeline — ตัดสินไว้ตอนคุยขอบเขต (โน้ตเป็นของผู้เขียนเอง)"""
    cur = conn.cursor()
    cur.execute("DELETE FROM case_notes WHERE id = %s", (note_id,))
    conn.commit()


def add_event(conn, case_id: int, actor, kind: str, detail: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO case_events (case_id, actor_id, kind, detail, created_at) VALUES (%s, %s, %s, %s, %s)",
        (case_id, actor.id, kind, detail[:500], datetime.now()),
    )
    conn.commit()


def list_events(conn, case_id: int) -> list[CaseEvent]:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM case_events WHERE case_id = %s ORDER BY created_at DESC, id DESC", (case_id,))
    return [
        CaseEvent(
            case_id=row["case_id"], actor=get_user_by_id(conn, row["actor_id"]), kind=row["kind"],
            detail=row["detail"], created_at=row["created_at"], id=row["id"],
        )
        for row in cur.fetchall()
    ]


def latest_event_by_case(conn, case_ids: list[int]) -> dict[int, tuple[str, datetime]]:
    """เหตุการณ์ล่าสุดของแต่ละคดี (detail, created_at) — คอลัมน์ "อัปเดตล่าสุด" หน้าคดีต่อทนายของ manager"""
    if not case_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(case_ids))
    cur = conn.cursor(dictionary=True)
    cur.execute(
        f"""SELECT e.case_id, e.detail, e.created_at FROM case_events e
            JOIN (SELECT case_id, MAX(id) AS last_id FROM case_events
                  WHERE case_id IN ({placeholders}) GROUP BY case_id) m ON e.id = m.last_id""",
        tuple(case_ids),
    )
    return {row["case_id"]: (row["detail"], row["created_at"]) for row in cur.fetchall()}
