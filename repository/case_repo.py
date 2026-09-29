"""BL-18: repository ของตาราง cases — find_by_case_no ค้นทั้งเลขคดีดำและคดีแดง

หมายเหตุ: get_by_id()/find_by_case_no() คืน Case ที่ _assignments ยังว่างอยู่
เรียก AssignmentRepository.list_for_case() แล้ว extend เข้า case._assignments เอง ถ้าต้องใช้ lawyers()/lead_lawyer()
"""

from datetime import datetime

from domain.case import Case, CaseEvent, CaseNote, CaseStatus
from repository.client_repo import ClientRepository
from repository.user_repo import UserRepository


class CaseRepository:
    """ที่เก็บคดี — ถือ connection ไว้หนึ่งตัว เมธอดชื่อเดิม (ตัดพารามิเตอร์ conn ตัวแรกออก)

    ประกอบ object ลูก (ลูกความ, ผู้เขียนโน้ต/เหตุการณ์) ผ่าน repository เพื่อนที่ใช้ connection เดียวกัน —
    รับมาจากข้างนอกได้ หรือให้สร้างเองก็ได้
    """

    def __init__(self, conn, clients: ClientRepository | None = None, users: UserRepository | None = None):
        self._conn = conn
        self._clients = clients or ClientRepository(conn)
        self._users = users or UserRepository(conn)

    def _row_to_case(self, row: dict) -> Case:
        client = self._clients.get_by_id(row["client_id"])
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

    def get_by_id(self, case_id: int) -> Case | None:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
        row = cur.fetchone()
        return self._row_to_case(row) if row else None

    def find_by_case_no(self, case_no: str) -> Case | None:
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM cases WHERE black_case_no = %s OR red_case_no = %s", (case_no, case_no)
        )
        row = cur.fetchone()
        return self._row_to_case(row) if row else None

    def list_accepted_by_lawyer(self, lawyer_id: int) -> list[Case]:
        """คดีที่ทนายคนนี้ตอบรับแล้ว — ใช้เลือกคดีตอนสร้างนัดใหม่ (BL-20)"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            """SELECT DISTINCT c.* FROM cases c
               JOIN case_assignments a ON a.case_id = c.id
               WHERE a.lawyer_id = %s AND a.status = 'accepted'
               ORDER BY c.title""",
            (lawyer_id,),
        )
        return [self._row_to_case(row) for row in cur.fetchall()]

    def list_without_accepted_lawyer(self) -> list[Case]:
        """คดีที่ยังไม่มีทนายตอบรับ ไม่รวมคดีที่ปิด/ยกเลิกแล้ว — กล่องแจ้งเตือนของ manager (BL-26)
        รวมคดีที่มอบหมายแล้วแต่ทนายยังไม่ตอบ (pending) — คือ "ทนายไม่ตอบรับ" ที่ manager ต้องตามต่อ
        """
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.* FROM cases c
               WHERE c.status NOT IN ('closed', 'cancelled')
               AND NOT EXISTS (
                   SELECT 1 FROM case_assignments a WHERE a.case_id = c.id AND a.status = 'accepted'
               )
               ORDER BY c.opened_date"""
        )
        return [self._row_to_case(row) for row in cur.fetchall()]

    def add(self, case: Case) -> Case:
        cur = self._conn.cursor()
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
        self._conn.commit()
        case.id = cur.lastrowid
        return case

    def update_progress(self, case: Case) -> None:
        """เขียนสถานะและเลขคดีดำ/แดงปัจจุบันลง DB — เลขซ้ำกับคดีอื่นโยน mysql.connector.IntegrityError (UNIQUE)"""
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE cases SET status = %s, black_case_no = %s, red_case_no = %s WHERE id = %s",
            (case.status.value, case.black_case_no, case.red_case_no, case.id),
        )
        self._conn.commit()

    def add_note(self, note: CaseNote) -> CaseNote:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO case_notes (case_id, author_id, text, created_at) VALUES (%s, %s, %s, %s)",
            (note.case_id, note.author.id, note.text, note.created_at),
        )
        self._conn.commit()
        note.id = cur.lastrowid
        return note

    def get_note(self, note_id: int) -> CaseNote | None:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM case_notes WHERE id = %s", (note_id,))
        row = cur.fetchone()
        return self._row_to_note(row) if row else None

    def list_notes(self, case_id: int) -> list[CaseNote]:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM case_notes WHERE case_id = %s ORDER BY created_at DESC, id DESC", (case_id,))
        return [self._row_to_note(row) for row in cur.fetchall()]

    def _row_to_note(self, row: dict) -> CaseNote:
        return CaseNote(
            case_id=row["case_id"], author=self._users.get_by_id(row["author_id"]),
            text=row["text"], created_at=row["created_at"], id=row["id"],
        )

    def update_note(self, note: CaseNote) -> None:
        cur = self._conn.cursor()
        cur.execute("UPDATE case_notes SET text = %s WHERE id = %s", (note.text, note.id))
        self._conn.commit()

    def delete_note(self, note_id: int) -> None:
        """ลบจริง ไม่ลง timeline — ตัดสินไว้ตอนคุยขอบเขต (โน้ตเป็นของผู้เขียนเอง)"""
        cur = self._conn.cursor()
        cur.execute("DELETE FROM case_notes WHERE id = %s", (note_id,))
        self._conn.commit()

    def add_event(self, case_id: int, actor, kind: str, detail: str) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO case_events (case_id, actor_id, kind, detail, created_at) VALUES (%s, %s, %s, %s, %s)",
            (case_id, actor.id, kind, detail[:500], datetime.now()),
        )
        self._conn.commit()

    def list_events(self, case_id: int) -> list[CaseEvent]:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM case_events WHERE case_id = %s ORDER BY created_at DESC, id DESC", (case_id,))
        return [
            CaseEvent(
                case_id=row["case_id"], actor=self._users.get_by_id(row["actor_id"]), kind=row["kind"],
                detail=row["detail"], created_at=row["created_at"], id=row["id"],
            )
            for row in cur.fetchall()
        ]

    def latest_event_by_case(self, case_ids: list[int]) -> dict[int, tuple[str, datetime]]:
        """เหตุการณ์ล่าสุดของแต่ละคดี (detail, created_at) — คอลัมน์ "อัปเดตล่าสุด" หน้าคดีต่อทนายของ manager"""
        if not case_ids:
            return {}
        placeholders = ", ".join(["%s"] * len(case_ids))
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            f"""SELECT e.case_id, e.detail, e.created_at FROM case_events e
                JOIN (SELECT case_id, MAX(id) AS last_id FROM case_events
                      WHERE case_id IN ({placeholders}) GROUP BY case_id) m ON e.id = m.last_id""",
            tuple(case_ids),
        )
        return {row["case_id"]: (row["detail"], row["created_at"]) for row in cur.fetchall()}
