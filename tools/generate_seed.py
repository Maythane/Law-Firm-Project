"""BL-19: สร้าง db/seed.sql — ข้อมูลตัวอย่างสำหรับสาธิต/ตรวจงาน (อยู่นอก domain/ ไม่ใช่ส่วนที่ส่งมอบ)

ใช้ random.seed() คงที่ (ชื่อ/การกระจายข้อมูลเหมือนเดิมทุกครั้ง) + date.today() เป็นจุดยึด
(นัดคร่อมวันที่รันเสมอ) — รันวันเดียวกันได้ผลเดิม รันคนละวันได้ข้อมูลขยับตามวันนั้นแต่โครงเหมือนเดิม

รัน:  python tools/generate_seed.py   -> เขียนไฟล์ db/seed.sql
ดูขอบเขตงานเต็มที่ backlog.md#bl-19
"""

import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # ให้ import "api.*"/"domain.*" ได้ไม่ว่ารันจากไหน

from api.auth import hash_password  # noqa: E402

RANDOM_SEED = 42
TODAY = date.today()
DEMO_PASSWORD = "password123"  # บัญชีตัวอย่างทั้งหมดใช้รหัสผ่านเดียวกัน — README (BL-22) จะบอกไว้

FIRST_NAMES = [
    "สมชาย", "สมหญิง", "วิชัย", "วิภา", "ประเสริฐ", "อรุณี", "ธนา", "กาญจนา", "สุรชัย", "พิมพ์ใจ",
    "ชัยวัฒน์", "รัตนา", "ณัฐพล", "สุภาพร", "อนุชา", "จิรา", "เกียรติศักดิ์", "วรรณา", "ปิยะ", "ศิริพร",
    "มานพ", "อำไพ", "สมบูรณ์", "ละเอียด", "วิรัตน์", "ปราณี", "สมพงษ์", "ดวงใจ", "ชูเกียรติ", "นงลักษณ์",
]
LAST_NAMES = [
    "ใจดี", "รักชาติ", "เพียรกิจ", "มั่นคง", "ศรีสุข", "แสงทอง", "บุญมี", "ทองดี", "รุ่งเรือง", "สว่างวงศ์",
]
CASE_TITLES = [
    "ผิดสัญญาซื้อขาย", "เรียกค่าเสียหายจากละเมิด", "ฟ้องหย่าและแบ่งสินสมรส", "ผิดสัญญาเช่า",
    "เรียกหนี้เงินกู้", "ขับไล่ผู้เช่า", "ฟ้องแบ่งมรดก", "เรียกค่าชดเชยแรงงาน",
    "ผิดสัญญาจ้างทำของ", "ละเมิดลิขสิทธิ์", "เรียกค่าสินไหมประกันภัย", "ผิดสัญญาค้ำประกัน",
]
COURT_NAMES = ["ศาลแพ่งกรุงเทพใต้", "ศาลแพ่งมีนบุรี", "ศาลจังหวัดนนทบุรี", "ศาลแพ่งธนบุรี"]
CASE_STATUSES_IN_ORDER = ["open", "filed", "trial", "judged", "final", "closed", "cancelled"]


def _sql_str(value) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _sql_bool(value: bool) -> str:
    return "1" if value else "0"


def _sql_dt(value) -> str:
    if value is None:
        return "NULL"
    return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"


def _sql_date(value) -> str:
    if value is None:
        return "NULL"
    return "'" + value.strftime("%Y-%m-%d") + "'"


def gen_users() -> list[dict]:
    users = [
        dict(id=1, role="admin", name="แอดมิน ระบบ", citizen_id="1000000000001", phone="020000001",
             username="admin", license_no=None),
        dict(id=2, role="manager", name=f"{FIRST_NAMES[0]} {LAST_NAMES[0]}", citizen_id="1000000000002",
             phone="020000002", username="manager1", license_no=None),
    ]
    for i in range(8):
        users.append(dict(
            id=3 + i, role="lawyer",
            name=f"{FIRST_NAMES[(i + 1) % len(FIRST_NAMES)]} {LAST_NAMES[(i + 1) % len(LAST_NAMES)]}",
            citizen_id=f"100000000{10 + i}", phone=f"08{10000000 + i}",
            username=f"lawyer{i + 1}", license_no=f"LAW-{2000 + i}",
        ))
    password_hash = hash_password(DEMO_PASSWORD)
    for u in users:
        u["password_hash"] = password_hash
        u["is_active"] = True
    return users


def gen_clients(n: int) -> list[dict]:
    clients = []
    for i in range(n):
        has_company = i % 4 == 0
        clients.append(dict(
            id=i + 1,
            name=f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[i % len(LAST_NAMES)]}",
            citizen_id=f"2{i:012d}",
            phone=f"09{i:08d}",
            company=f"บจก. {LAST_NAMES[i % len(LAST_NAMES)]} กรุ๊ป" if has_company else None,
        ))
    return clients


def gen_cases(n: int, client_ids: list[int]) -> list[dict]:
    cases = []
    black_seq = 1
    red_seq = 1
    for i in range(n):
        status = CASE_STATUSES_IN_ORDER[i] if i < len(CASE_STATUSES_IN_ORDER) else random.choices(
            ["open", "filed", "trial", "judged", "final", "closed"],
            weights=[30, 25, 15, 10, 10, 10],
        )[0]
        opened = TODAY - timedelta(days=random.randint(10, 400))
        filed_date = None
        black_case_no = None
        red_case_no = None
        if status != "open":
            filed_date = opened + timedelta(days=random.randint(3, 30))
            black_case_no = f"{black_seq}/2568"
            black_seq += 1
        if status in ("judged", "final", "closed"):
            red_case_no = f"{red_seq}/2569"
            red_seq += 1
        cases.append(dict(
            id=i + 1,
            title=random.choice(CASE_TITLES),
            black_case_no=black_case_no,
            red_case_no=red_case_no,
            client_id=random.choice(client_ids),
            client_role=random.choice(["โจทก์", "จำเลย"]),
            opposing_party=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            court_name=random.choice(COURT_NAMES),
            status=status,
            opened_date=opened,
            filed_date=filed_date,
        ))
    return cases


def gen_assignments(cases: list[dict], lawyer_ids: list[int], manager_id: int) -> list[dict]:
    assignments = []
    aid = 1
    pending_left, declined_left = 5, 3
    for case in cases:
        needs_accepted = case["status"] != "open"
        available = lawyer_ids[:]
        random.shuffle(available)
        num_for_case = 1 if not needs_accepted else random.choice([1, 1, 2])
        assigned_here = 0
        for lawyer_id in available[: num_for_case + 1]:
            if declined_left > 0 and random.random() < 0.15:
                status, decline_reason, responded = "declined", "ภาระงานล้นมือช่วงนี้", TODAY - timedelta(days=2)
                declined_left -= 1
            elif needs_accepted and assigned_here == 0:
                status, decline_reason, responded = "accepted", None, TODAY - timedelta(days=5)
            elif pending_left > 0 and random.random() < 0.3:
                status, decline_reason, responded = "pending", None, None
                pending_left -= 1
            else:
                status, decline_reason, responded = "accepted", None, TODAY - timedelta(days=5)

            assignments.append(dict(
                id=aid, case_id=case["id"], lawyer_id=lawyer_id, assigned_by=manager_id,
                assigned_at=datetime.combine(TODAY - timedelta(days=6), datetime.min.time()),
                status=status,
                responded_at=datetime.combine(responded, datetime.min.time()) if responded else None,
                decline_reason=decline_reason,
                is_lead=(status == "accepted" and assigned_here == 0),
            ))
            if status == "accepted":
                assigned_here += 1
            aid += 1
            if assigned_here >= num_for_case:
                break
    # เติม pending/declined ที่ยังไม่ครบโควตาเข้าไปในคดีเปิดใหม่ๆ ท้ายลิสต์
    extra_pool = [c for c in cases if c["status"] == "open"]
    while pending_left > 0 and extra_pool:
        case = random.choice(extra_pool)
        lawyer_id = random.choice(lawyer_ids)
        assignments.append(dict(
            id=aid, case_id=case["id"], lawyer_id=lawyer_id, assigned_by=manager_id,
            assigned_at=datetime.combine(TODAY - timedelta(days=1), datetime.min.time()),
            status="pending", responded_at=None, decline_reason=None, is_lead=False,
        ))
        aid += 1
        pending_left -= 1
    return assignments


def _accepted_lawyers_by_case(assignments: list[dict]) -> dict[int, list[int]]:
    by_case: dict[int, list[int]] = {}
    for a in assignments:
        if a["status"] == "accepted":
            by_case.setdefault(a["case_id"], []).append(a["lawyer_id"])
    return by_case


def gen_appointments(cases: list[dict], assignments: list[dict], target: int) -> list[dict]:
    accepted_by_case = _accepted_lawyers_by_case(assignments)
    eligible_cases = [c for c in cases if c["id"] in accepted_by_case]
    appointments = []
    aid = 1

    def add_appointment(case_id, lawyer_id, kind, starts_at, ends_at, **extra):
        nonlocal aid
        row = dict(
            id=aid, case_id=case_id, lawyer_id=lawyer_id, kind=kind,
            starts_at=starts_at, ends_at=ends_at, location=extra.get("location", "สำนักงานความ"),
            court_name=extra.get("court_name"), room_no=extra.get("room_no"),
            triggered_by_event=extra.get("triggered_by_event"),
            is_done=extra.get("is_done", False), is_cancelled=False, cancel_reason=None,
        )
        appointments.append(row)
        aid += 1
        return row

    # นัดของ "วันนี้" ให้ทนายหลายคนเห็นตารางวันนี้มีของแน่นอน
    for i, lawyer_id in enumerate(sorted({lid for lids in accepted_by_case.values() for lid in lids})[:6]):
        case = random.choice([c for c in eligible_cases if lawyer_id in accepted_by_case[c["id"]]])
        hour = 9 + i
        add_appointment(
            case["id"], lawyer_id, "meeting",
            datetime.combine(TODAY, datetime.min.time()) + timedelta(hours=hour),
            datetime.combine(TODAY, datetime.min.time()) + timedelta(hours=hour + 1),
        )

    # กำหนดยื่นเอกสารที่เหลือน้อยกว่า 14 วัน 4 รายการ
    for i in range(4):
        case = random.choice(eligible_cases)
        lawyer_id = random.choice(accepted_by_case[case["id"]])
        deadline_day = TODAY + timedelta(days=2 + i * 3)
        add_appointment(
            case["id"], lawyer_id, "deadline",
            datetime.combine(deadline_day, datetime.min.time()),
            datetime.combine(deadline_day, datetime.min.time().replace(hour=23, minute=59)),
            location="-", triggered_by_event="อ่านคำพิพากษา",
        )

    def has_conflict(lawyer_id, starts_at, ends_at) -> bool:
        return any(
            a["lawyer_id"] == lawyer_id and a["kind"] != "deadline"
            and starts_at < a["ends_at"] and a["starts_at"] < ends_at
            for a in appointments
        )

    # นัดทั่วไปกระจายรอบวันนี้ +/- ~90 วัน จนครบเป้าหมาย — กันชนกันเองโดยไม่ได้ตั้งใจ
    # (นัดชนที่ต้องมีคือ 2 คู่ที่ใส่ตั้งใจด้านล่างเท่านั้น)
    while len(appointments) < target:
        case = random.choice(eligible_cases)
        lawyer_id = random.choice(accepted_by_case[case["id"]])
        kind = random.choices(["hearing", "meeting"], weights=[40, 60])[0]
        for _attempt in range(20):
            offset_days = random.randint(-60, 90)
            hour = random.randint(9, 15)
            starts_at = datetime.combine(TODAY + timedelta(days=offset_days), datetime.min.time()) + timedelta(hours=hour)
            ends_at = starts_at + timedelta(hours=1)
            if not has_conflict(lawyer_id, starts_at, ends_at):
                break
        else:
            continue  # หาช่วงว่างไม่เจอใน 20 ครั้ง ข้ามรอบนี้ไปสุ่มใหม่
        if kind == "hearing":
            add_appointment(
                case["id"], lawyer_id, "hearing", starts_at, ends_at,
                location=random.choice(COURT_NAMES), court_name=random.choice(COURT_NAMES),
                room_no=str(random.randint(1, 20)),
                is_done=offset_days < -3,
            )
        else:
            add_appointment(case["id"], lawyer_id, "meeting", starts_at, ends_at, is_done=offset_days < -3)

    # จงใจใส่นัดชน 2 คู่ (ทนายคนเดียวกัน เวลาเหลื่อมกัน) — ข้อมูลตัวอย่างสำหรับสาธิต ไม่ได้ผ่าน Schedule.add()
    # หยิบจากท้ายลิสต์ (กลุ่มนัดทั่วไป) ไม่เอาจากนัด "วันนี้" ที่ตั้งใจให้สะอาดไว้โชว์
    conflict_pairs = 0
    for row in reversed(list(appointments)):
        if conflict_pairs >= 2 or row["kind"] == "deadline":
            continue
        add_appointment(
            row["case_id"], row["lawyer_id"], row["kind"],
            row["starts_at"] + timedelta(minutes=30), row["ends_at"] + timedelta(minutes=30),
            location=row["location"], court_name=row["court_name"], room_no=row["room_no"],
        )
        conflict_pairs += 1

    return appointments


def gen_appointment_changes(appointments: list[dict], target: int) -> list[dict]:
    reschedulable = [a for a in appointments if a["kind"] != "deadline"]
    changes = []
    for i in range(min(target, len(reschedulable))):
        appt = reschedulable[i]
        old_start = appt["starts_at"]
        new_start = old_start + timedelta(days=random.choice([1, 2, 3, -1]))
        changes.append(dict(
            id=i + 1, appointment_id=appt["id"], old_starts_at=old_start, new_starts_at=new_start,
            reason=random.choice(["ลูกความติดธุระ", "ทนายติดว่าความคดีอื่น", "ศาลเลื่อนนัด", "เลื่อนตามคำขอคู่ความ"]),
            changed_at=datetime.combine(TODAY - timedelta(days=random.randint(1, 20)), datetime.min.time()),
        ))
    return changes


def _insert_sql(table: str, columns: list[str], rows: list[dict], formatters: dict) -> str:
    if not rows:
        return ""
    lines = [f"INSERT INTO {table} ({', '.join(columns)}) VALUES"]
    value_lines = []
    for row in rows:
        formatted = [formatters.get(col, _sql_str)(row[col]) for col in columns]
        value_lines.append("(" + ", ".join(formatted) + ")")
    lines.append(",\n".join(value_lines) + ";\n")
    return "\n".join(lines)


def build_seed_sql() -> str:
    random.seed(RANDOM_SEED)

    users = gen_users()
    clients = gen_clients(40)
    cases = gen_cases(60, [c["id"] for c in clients])
    manager_id = next(u["id"] for u in users if u["role"] == "manager")
    lawyer_ids = [u["id"] for u in users if u["role"] == "lawyer"]
    assignments = gen_assignments(cases, lawyer_ids, manager_id)
    appointments = gen_appointments(cases, assignments, target=250)
    changes = gen_appointment_changes(appointments, target=30)

    parts = ["-- BL-19: สร้างโดย tools/generate_seed.py — ห้ามแก้ไฟล์นี้ตรงๆ ให้แก้สคริปต์แล้วรันใหม่\n"]
    parts.append(_insert_sql(
        "users",
        ["id", "role", "name", "citizen_id", "phone", "username", "password_hash", "license_no", "is_active"],
        users, {"is_active": _sql_bool},
    ))
    parts.append(_insert_sql(
        "clients", ["id", "name", "citizen_id", "phone", "company"], clients, {},
    ))
    parts.append(_insert_sql(
        "cases",
        ["id", "title", "black_case_no", "red_case_no", "client_id", "client_role", "opposing_party",
         "court_name", "status", "opened_date", "filed_date"],
        cases, {"opened_date": _sql_date, "filed_date": _sql_date},
    ))
    parts.append(_insert_sql(
        "case_assignments",
        ["id", "case_id", "lawyer_id", "assigned_by", "assigned_at", "status", "responded_at",
         "decline_reason", "is_lead"],
        assignments, {"assigned_at": _sql_dt, "responded_at": _sql_dt, "is_lead": _sql_bool},
    ))
    parts.append(_insert_sql(
        "appointments",
        ["id", "case_id", "lawyer_id", "kind", "starts_at", "ends_at", "location", "court_name",
         "room_no", "triggered_by_event", "is_done", "is_cancelled", "cancel_reason"],
        appointments, {"starts_at": _sql_dt, "ends_at": _sql_dt, "is_done": _sql_bool, "is_cancelled": _sql_bool},
    ))
    parts.append(_insert_sql(
        "appointment_changes",
        ["id", "appointment_id", "old_starts_at", "new_starts_at", "reason", "changed_at"],
        changes, {"old_starts_at": _sql_dt, "new_starts_at": _sql_dt, "changed_at": _sql_dt},
    ))
    return "\n".join(p for p in parts if p)


def main():
    sql = build_seed_sql()
    out_path = Path(__file__).resolve().parent.parent / "db" / "seed.sql"
    out_path.write_text(sql, encoding="utf-8")
    print(f"เขียน {out_path} เรียบร้อยแล้ว")


if __name__ == "__main__":
    main()
