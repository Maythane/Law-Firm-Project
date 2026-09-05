# ผังคลาสและผังฐานข้อมูล — ฉบับปัจจุบัน

นายเมทนี พูลสมบัติ 6821500060 · แก้ล่าสุด 30 สิงหาคม 2569

ขอบเขตตาม [`backlog.md`](backlog.md) — ไม่มีประเภทคดี ไม่มีชั่วโมงทำงานและค่าจ้าง
draw.io วางผัง mermaid ได้ที่ **Arrange → Insert → Advanced → Mermaid**

---

## 1. ผังคลาส — คน สิทธิ์ และการมอบหมาย

```mermaid
classDiagram
    class Person {
        <<abstract>>
        -name
        -citizen_id
        -phone
        +display_name()*
        +contact_info()
    }
    class SystemUser {
        <<abstract>>
        -username
        -password_hash
        -is_active
        +can_view_case(case)*
        +dashboard_cards()*
        +check_password(raw)
    }
    class Lawyer {
        -license_no
        +display_name()
        +can_view_case(case)
        +dashboard_cards()
        +workload()
    }
    class Manager {
        +can_view_case(case)
        +dashboard_cards()
        +assign(case, lawyer)
    }
    class Admin {
        +can_view_case(case)
        +dashboard_cards()
        +deactivate(user)
    }
    class Client {
        -company
        +display_name()
    }
    class CaseAssignment {
        -assigned_at
        -status
        -responded_at
        -decline_reason
        -is_lead
        +accept()
        +decline(reason)
        +is_pending()
    }
    class AssignmentStatus {
        <<enumeration>>
        PENDING
        ACCEPTED
        DECLINED
    }

    Person <|-- SystemUser
    Person <|-- Client
    SystemUser <|-- Lawyer
    SystemUser <|-- Manager
    SystemUser <|-- Admin
    CaseAssignment "*" --> "1" Lawyer : มอบหมายให้
    CaseAssignment "*" --> "1" Manager : assigned_by
    CaseAssignment --> AssignmentStatus
    CaseAssignment "*" --> "1" Case : คดีที่มอบหมาย
```

---

## 2. ผังคลาส — คดี นัดหมาย และตารางนัด

```mermaid
classDiagram
    class Case {
        -title
        -black_case_no
        -red_case_no
        -client_role
        -opposing_party
        -court_name
        -opened_date
        -filed_date
        -status
        +display_black_no()
        +display_red_no()
        +assign_red_number()
        +advance_status()
        +can_close()
        +lawyers()
        +lead_lawyer()
    }
    class CaseStatus {
        <<enumeration>>
        เปิดคดี
        ยื่นฟ้อง
        สืบพยาน
        ตัดสิน
        ถึงที่สุด
        ปิดคดี
        ยกเลิก
    }
    class Appointment {
        <<abstract>>
        -starts_at
        -ends_at
        -location
        -is_done
        +reminder_lead_days()*
        +can_reschedule()*
        +kind_label()*
        +overlaps(other)
        +is_due_soon(today)
        +reschedule(new_time, reason)
        +cancel(reason)
    }
    class CourtHearing {
        -court_name
        -room_no
        +reminder_lead_days()
        +can_reschedule()
        +kind_label()
    }
    class ClientMeeting {
        +reminder_lead_days()
        +can_reschedule()
        +kind_label()
    }
    class FilingDeadline {
        -triggered_by_event
        +reminder_lead_days()
        +can_reschedule()
        +kind_label()
        +from_event()$
    }
    class AppointmentChange {
        -old_starts_at
        -new_starts_at
        -reason
        -changed_at
    }
    class Schedule {
        +add(appointment)
        +day_view(lawyer, day)
        +week_view(lawyer, week)
        +month_view(lawyer, y, m)
        +find_conflicts(appointment)
        +upcoming_reminders(today)
    }
    class LawFirm {
        +open_case()
        +assign_lawyer()
        +find_by_case_no()
        +search()
    }

    Case --> CaseStatus
    Appointment <|-- CourtHearing
    Appointment <|-- ClientMeeting
    Appointment <|-- FilingDeadline
    Case "1" --> "1" Client
    Case "1" --> "*" Appointment
    Case "1" --> "*" CaseAssignment
    Appointment "1" --> "1" Lawyer : เจ้าของนัด
    Appointment "1" --> "*" AppointmentChange : ประวัติการเลื่อน
    Schedule "1" --> "*" Appointment
    LawFirm "1" --> "*" Case
    LawFirm "1" --> "1" Schedule
    LawFirm "1" --> "*" SystemUser
```

**จุดที่ใช้ polymorphism** — `Appointment` 3 ชนิดตอบ `reminder_lead_days()` และ `can_reschedule()` คนละแบบ · `SystemUser` 3 บทบาทตอบ `can_view_case()` และ `dashboard_cards()` คนละแบบ ทำให้ทั้งระบบตรวจสิทธิ์ที่จุดเดียวโดยไม่มี `if role ==`

---

## 3. ผังฐานข้อมูล — 6 ตาราง

```mermaid
erDiagram
    CLIENTS ||--o{ CASES : "เป็นลูกความของ"
    CASES ||--o{ CASE_ASSIGNMENTS : "มอบหมาย"
    USERS ||--o{ CASE_ASSIGNMENTS : "ทนายที่รับผิดชอบ"
    USERS ||--o{ CASE_ASSIGNMENTS : "ผู้มอบหมาย"
    CASES ||--o{ APPOINTMENTS : "มีวันนัด"
    USERS ||--o{ APPOINTMENTS : "เจ้าของนัด"
    APPOINTMENTS ||--o{ APPOINTMENT_CHANGES : "ประวัติการเลื่อน"

    USERS {
        int id PK
        enum role "admin|manager|lawyer"
        varchar name
        varchar citizen_id
        varchar phone
        varchar username UK
        varchar password_hash
        varchar license_no "เฉพาะ lawyer"
        bool is_active
    }
    CLIENTS {
        int id PK
        varchar name
        varchar citizen_id
        varchar phone
        varchar company "ถ้าเป็นนิติบุคคล"
    }
    CASES {
        int id PK
        varchar title
        varchar black_case_no UK "หมายเลขคดีดำ"
        varchar red_case_no UK "หมายเลขคดีแดง ว่างได้"
        int client_id FK
        varchar client_role "โจทก์|จำเลย"
        varchar opposing_party
        varchar court_name
        enum status
        date opened_date
        date filed_date "ว่างได้ถ้ายังไม่ฟ้อง"
    }
    CASE_ASSIGNMENTS {
        int id PK
        int case_id FK
        int lawyer_id FK
        int assigned_by FK
        datetime assigned_at
        enum status "pending|accepted|declined"
        datetime responded_at "ว่างได้"
        varchar decline_reason "บังคับเมื่อปฏิเสธ"
        bool is_lead
    }
    APPOINTMENTS {
        int id PK
        int case_id FK
        int lawyer_id FK
        enum kind "hearing|meeting|deadline"
        datetime starts_at
        datetime ends_at
        varchar location
        varchar room_no "เฉพาะนัดศาล"
        varchar triggered_by_event "เฉพาะกำหนดยื่นเอกสาร"
        bool is_done
        varchar cancel_reason
        datetime cancelled_at
    }
    APPOINTMENT_CHANGES {
        int id PK
        int appointment_id FK
        datetime old_starts_at
        datetime new_starts_at
        varchar reason
        datetime changed_at
    }
```

```sql
CREATE UNIQUE INDEX idx_black ON cases(black_case_no);
CREATE UNIQUE INDEX idx_red   ON cases(red_case_no);
CREATE INDEX        idx_sched ON appointments(lawyer_id, starts_at);
CREATE UNIQUE INDEX idx_assign ON case_assignments(case_id, lawyer_id, status);
```

**หมายเหตุการออกแบบ**

- `users` รวมทั้งสามบทบาทไว้ตารางเดียว แยกด้วย `role` ชั้น Repository อ่านค่านี้แล้วสร้าง object ให้ตรงคลาส (`"lawyer"` → `Lawyer`)
- `appointments` ใช้ตารางเดียวเก็บนัดทั้งสามประเภท แยกด้วย `kind` เช่นเดียวกัน คอลัมน์ที่ใช้เฉพาะบางประเภทปล่อยว่างในประเภทที่ไม่ใช้
- `case_assignments` ไม่ใช่ตารางเชื่อมเปล่า มีข้อมูลของตัวเอง — สถานะการตอบรับ ผู้มอบหมาย เวลาที่ตอบ และเหตุผลที่ปฏิเสธ จึงยกขึ้นเป็นคลาส `CaseAssignment`
- `idx_assign` บังคับ BR-17 ที่ระดับฐานข้อมูล — มอบหมายคดีเดิมให้ทนายคนเดิมซ้ำในสถานะเดียวกันไม่ได้
- `idx_sched` รองรับคำถามที่ระบบถามบ่อยที่สุด คือ "ทนายคนนี้มีนัดอะไรช่วงเวลานี้บ้าง" ใช้ทั้งหน้าตารางประจำวันและการตรวจนัดชน

---

## 4. ตารางสำหรับกรอกชีต ER ของอาจารย์

รูปแบบ `Column Name | Data Type | Description | Key Type` ฉบับย่อ 3–5 แถวต่อตาราง

**Table: users**

| Column Name | Data Type | Description | Key Type |
|---|---|---|---|
| id | INT | รหัสผู้ใช้ | PK |
| role | ENUM('admin','manager','lawyer') | บทบาทในระบบ | |
| name | VARCHAR(120) | ชื่อ-นามสกุล | |
| username | VARCHAR(50) | ชื่อผู้ใช้สำหรับเข้าระบบ | UK |

**Table: clients**

| Column Name | Data Type | Description | Key Type |
|---|---|---|---|
| id | INT | รหัสลูกความ | PK |
| name | VARCHAR(120) | ชื่อ-นามสกุล | |
| phone | VARCHAR(20) | เบอร์ติดต่อ | |
| company | VARCHAR(150) | ชื่อบริษัท ถ้าเป็นนิติบุคคล | |

**Table: cases**

| Column Name | Data Type | Description | Key Type |
|---|---|---|---|
| id | INT | รหัสคดี | PK |
| black_case_no | VARCHAR(20) | หมายเลขคดีดำ | UK |
| client_id | INT | ลูกความเจ้าของคดี | FK → clients.id |
| status | ENUM('open','filed','trial','judged','closed') | สถานะปัจจุบันของคดี | |

**Table: case_assignments**

| Column Name | Data Type | Description | Key Type |
|---|---|---|---|
| id | INT | รหัสการมอบหมาย | PK |
| case_id | INT | คดีที่มอบหมาย | FK → cases.id |
| lawyer_id | INT | ทนายที่ได้รับมอบหมาย | FK → users.id |
| status | ENUM('pending','accepted','declined') | รอตอบรับ / ตอบรับ / ปฏิเสธ | |

**Table: appointments**

| Column Name | Data Type | Description | Key Type |
|---|---|---|---|
| id | INT | รหัสนัดหมาย | PK |
| case_id | INT | คดีที่นัดนี้สังกัด | FK → cases.id |
| lawyer_id | INT | ทนายเจ้าของนัด | FK → users.id |
| kind | ENUM('hearing','meeting','deadline') | ชนิดของนัด | |
| starts_at | DATETIME | วันเวลาที่นัด | |

**Table: appointment_changes**

| Column Name | Data Type | Description | Key Type |
|---|---|---|---|
| id | INT | รหัสรายการ | PK |
| appointment_id | INT | นัดที่ถูกเลื่อน | FK → appointments.id |
| new_starts_at | DATETIME | เวลาใหม่หลังเลื่อน | |
| reason | VARCHAR(255) | เหตุผลในการเลื่อน | |
