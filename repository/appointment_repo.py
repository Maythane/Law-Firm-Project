"""BL-18: repository ของตาราง appointments — อ่าน kind แล้วสร้าง object ให้ตรงคลาสลูก
ลบนัด = ทำเครื่องหมายยกเลิก ไม่ลบแถวจริง
"""

from domain.appointment import Appointment, ClientMeeting, CourtHearing, FilingDeadline
from repository.case_repo import CaseRepository
from repository.user_repo import UserRepository

_KIND_TO_CLASS = {"hearing": CourtHearing, "meeting": ClientMeeting, "deadline": FilingDeadline}
_CLASS_TO_KIND = {CourtHearing: "hearing", ClientMeeting: "meeting", FilingDeadline: "deadline"}


class AppointmentRepository:
    """ที่เก็บนัดหมาย — ถือ connection ไว้หนึ่งตัว เมธอดชื่อเดิม (ตัดพารามิเตอร์ conn ตัวแรกออก)"""

    def __init__(self, conn, cases: CaseRepository | None = None, users: UserRepository | None = None):
        self._conn = conn
        self._cases = cases or CaseRepository(conn)
        self._users = users or UserRepository(conn)

    def _row_to_appointment(self, row: dict) -> Appointment:
        cls = _KIND_TO_CLASS[row["kind"]]
        kwargs = dict(
            case=self._cases.get_by_id(row["case_id"]),
            lawyer=self._users.get_by_id(row["lawyer_id"]),
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            location=row["location"] or "",
            is_done=bool(row["is_done"]),
            is_cancelled=bool(row["is_cancelled"]),
            cancel_reason=row["cancel_reason"],
            id=row["id"],
        )
        if cls is CourtHearing:
            kwargs["court_name"] = row["court_name"] or ""
            kwargs["room_no"] = row["room_no"] or ""
        elif cls is FilingDeadline:
            kwargs["triggered_by_event"] = row["triggered_by_event"] or ""
        return cls(**kwargs)

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
        row = cur.fetchone()
        return self._row_to_appointment(row) if row else None

    def list_by_case(self, case_id: int) -> list[Appointment]:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM appointments WHERE case_id = %s", (case_id,))
        return [self._row_to_appointment(row) for row in cur.fetchall()]

    def list_by_lawyer(self, lawyer_id: int) -> list[Appointment]:
        """โหลดนัดที่ยังไม่ยกเลิกของทนายคนนี้ — ใช้ทำ day_view()/ตรวจนัดชนตอนสร้างนัดใหม่ (BL-20)"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM appointments WHERE lawyer_id = %s AND is_cancelled = 0", (lawyer_id,))
        return [self._row_to_appointment(row) for row in cur.fetchall()]

    def add(self, appt: Appointment) -> Appointment:
        kind = _CLASS_TO_KIND[type(appt)]
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO appointments
               (case_id, lawyer_id, kind, starts_at, ends_at, location,
                court_name, room_no, triggered_by_event, is_done, is_cancelled, cancel_reason)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                appt.case.id,
                appt.lawyer.id,
                kind,
                appt.starts_at,
                appt.ends_at,
                appt.location,
                getattr(appt, "court_name", None),
                getattr(appt, "room_no", None),
                getattr(appt, "triggered_by_event", None),
                appt.is_done,
                appt.is_cancelled,
                appt.cancel_reason,
            ),
        )
        self._conn.commit()
        appt.id = cur.lastrowid
        return appt

    def mark_done(self, appt: Appointment) -> None:
        """หายจากหน้าเตือนแต่ยังอยู่ในประวัติของคดี — FR-B4"""
        appt.is_done = True
        cur = self._conn.cursor()
        cur.execute("UPDATE appointments SET is_done = 1 WHERE id = %s", (appt.id,))
        self._conn.commit()

    def cancel(self, appt: Appointment, reason: str) -> None:
        """ลบนัด = ทำเครื่องหมายยกเลิก ไม่ลบแถวจริง"""
        appt.cancel(reason)  # ใช้กติกาจาก domain (บังคับมีเหตุผล) ก่อนค่อยเขียนลง DB
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE appointments SET is_cancelled = 1, cancel_reason = %s, cancelled_at = NOW() "
            "WHERE id = %s",
            (reason, appt.id),
        )
        self._conn.commit()

    def list_open_by_case_and_lawyer(self, case_id: int, lawyer_id: int) -> list[Appointment]:
        """นัดที่ยังไม่ถึง/ยังไม่เสร็จของทนายคนนี้ในคดีนี้ — แสดงตอน manager อนุมัติคำขอถอนตัว"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM appointments WHERE case_id = %s AND lawyer_id = %s "
            "AND is_cancelled = 0 AND is_done = 0 AND starts_at >= NOW() ORDER BY starts_at",
            (case_id, lawyer_id),
        )
        return [self._row_to_appointment(row) for row in cur.fetchall()]

    def reassign(self, appt: Appointment, new_lawyer) -> None:
        """ย้ายนัดไปทนายคนใหม่ (ตอนอนุมัติคำขอถอนตัว) — ผู้เรียกตรวจนัดชนมาแล้ว"""
        appt.lawyer = new_lawyer
        cur = self._conn.cursor()
        cur.execute("UPDATE appointments SET lawyer_id = %s WHERE id = %s", (new_lawyer.id, appt.id))
        self._conn.commit()
