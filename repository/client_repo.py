"""BL-18: repository ของตาราง clients"""

from domain.person import Client


def _row_to_client(row: dict) -> Client:
    return Client(
        name=row["name"],
        citizen_id=row["citizen_id"],
        phone=row["phone"],
        company=row["company"],
        id=row["id"],
    )


class ClientRepository:
    """ที่เก็บลูกความ — ถือ connection ไว้หนึ่งตัว เมธอดชื่อเดิม (ตัดพารามิเตอร์ conn ตัวแรกออก)"""

    def __init__(self, conn):
        self._conn = conn

    def get_by_id(self, client_id: int) -> Client | None:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
        row = cur.fetchone()
        return _row_to_client(row) if row else None

    def list_all(self) -> list[Client]:
        """รายชื่อลูกความทั้งหมด เรียงตามชื่อ — ใช้เลือกในฟอร์มเพิ่มคดีใหม่ (BL-31)"""
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM clients ORDER BY name")
        return [_row_to_client(row) for row in cur.fetchall()]

    def add(self, client: Client) -> Client:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO clients (name, citizen_id, phone, company) VALUES (%s, %s, %s, %s)",
            (client.name, client.citizen_id, client.phone, client.company),
        )
        self._conn.commit()
        client.id = cur.lastrowid
        return client
