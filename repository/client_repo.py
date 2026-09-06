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


def get_by_id(conn, client_id: int) -> Client | None:
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM clients WHERE id = %s", (client_id,))
    row = cur.fetchone()
    return _row_to_client(row) if row else None


def add(conn, client: Client) -> Client:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clients (name, citizen_id, phone, company) VALUES (%s, %s, %s, %s)",
        (client.name, client.citizen_id, client.phone, client.company),
    )
    conn.commit()
    client.id = cur.lastrowid
    return client
