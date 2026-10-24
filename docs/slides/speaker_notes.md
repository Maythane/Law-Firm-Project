# Speaker notes · Law Firm OOP

ไฟล์หลัก 13 หน้า (นำเสนอ ~10 นาที) ตามด้วยสไลด์สำรอง เปิดเมื่อถูกถาม

---

## หน้า 1 · ปก: ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ

**บนสไลด์**

- ระบบผู้ช่วยจัดการคดี
- และตารางนัดหมายสำหรับทนายความ
- Law Firm Case & Schedule Assistant · การออกแบบเชิง OOP
- นายเมทนี พูลสมบัติ  ·  รหัสนักศึกษา 6821500060
- FastAPI · Jinja2 · MariaDB · pytest

**พูด**

สวัสดีครับ ผมนายเมทนี พูลสมบัติ รหัส 6821500060 วันนี้จะนำเสนองานวิชา Object-Oriented Programming คือระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ ก่อนเริ่ม ขอบอกว่าทุกข้ออ้างในสไลด์ชุดนี้ชี้ไปที่โค้ดจริงใน repo ใต้ตัวอย่างโค้ดจะมีชื่อไฟล์และบรรทัดกำกับไว้ อาจารย์เปิดตรวจตามได้ทันทีครับ

---

## หน้า 2 · จัดงานด้วยสมุดและแชต ทำให้นัดชนและกำหนดหลุด

**บนสไลด์**

- ปัญหาและผู้ใช้ 3 บทบาท
- รับนัดใหม่โดยไม่รู้ว่าวันนั้นมีนัดอีกคดีอยู่แล้ว
- กำหนดยื่นตามกฎหมาย (คำให้การ / อุทธรณ์ / ฎีกา) ไม่มีอะไรนับวันให้
- มอบหมายทางแชต ไม่รู้ว่าทนายเห็น รับไหว หรือรับไปแล้ว
- แจกคดีใหม่โดยไม่เห็นว่าทนายแต่ละคนงานแน่นแค่ไหน

**ทนาย**

- ดูนัดวันนี้ ตอบรับ/ปฏิเสธคดี ดูรายการใกล้ครบกำหนด

**ผู้จัดการ**

- มอบหมายคดีตามภาระงาน เปิดคดีใหม่ อนุมัติคำขอถอนตัว

**แอดมิน**

- จัดการบัญชีผู้ใช้ ไม่เห็นเนื้อหาคดี

**พูด**

ปัญหาตั้งต้นมาจากสำนักงานกฎหมายที่ยังใช้สมุดกับแชตจัดงาน มีสี่เรื่อง หนึ่ง รับนัดใหม่โดยไม่รู้ว่าวันนั้นมีนัดคดีอื่นอยู่แล้ว สอง กำหนดยื่นตามกฎหมาย เช่น คำให้การ อุทธรณ์ ฎีกา ไม่มีอะไรนับวันให้ สาม มอบหมายงานทางแชต ไม่รู้ว่าทนายเห็นหรือรับงานแล้วหรือยัง และสี่ แจกคดีใหม่โดยไม่เห็นว่าใครงานแน่นแค่ไหน ระบบจึงมีผู้ใช้สามบทบาท ทนายดูนัดวันนี้และตอบรับคดี ผู้จัดการมอบหมายคดีตามภาระงาน และแอดมินจัดการบัญชี โดยแอดมินไม่เห็นเนื้อหาคดีเลยครับ

---

## หน้า 3 · เว็บแอปเดียวบน FastAPI + MariaDB แยกหน้าแรกตามบทบาท

**บนสไลด์**

- ภาพรวมระบบ · tech stack
- ทนาย → /schedule/today
- ผู้จัดการ → /manager/dashboard
- แอดมิน → /admin/dashboard

**Web layer**

- FastAPI 0.115 · Jinja2 · Pico.css + HTMX
- scrypt + signed-cookie session

**Data + infra**

- MariaDB 10.4 · mysql-connector ไม่ใช้ ORM
- Docker + phpMyAdmin · pytest 90 เทส

**พูด**

ภาพรวมระบบเป็นเว็บเดียวใช้ฐานข้อมูลเดียว ฝั่งเว็บใช้ FastAPI กับ Jinja2 template ตกแต่งด้วย Pico.css และ HTMX ฝั่งข้อมูลใช้ MariaDB ต่อผ่าน mysql-connector ตรงๆ ไม่ใช้ ORM รันด้วย Docker และทดสอบด้วย pytest 90 เทส ผู้ใช้ล็อกอินครั้งเดียว แล้วหน้า dashboard จะพาไปหน้าแรกตามบทบาทของตัวเอง ภาพทั้งสามคือหน้าจริงจากระบบ ทนายเห็นปฏิทินกับรายการใกล้ครบกำหนด ผู้จัดการเห็นคิวงานและภาระงานของทนายแต่ละคน แอดมินเห็นแค่จำนวนผู้ใช้ รหัสผ่านเก็บแบบ scrypt และแสดงวันที่เป็น พ.ศ. แต่เก็บเป็น ค.ศ. ต่อไปจะเข้าเรื่องการออกแบบครับ

---

## หน้า 4 · Person → SystemUser → ผู้ใช้ 3 บทบาท · Client สืบจาก Person

**บนสไลด์**

- CLASS DIAGRAM ฝั่งคน (1/2) · ลูกศรหัวสามเหลี่ยม = สืบทอด
- * = abstract method
- ลูกต้อง override
- Person «abstract»
- name · citizen_id · phone
- display_name()* · contact_info()
- SystemUser «abstract»
- username · password_hash · is_active
- can_view_case()* · dashboard_cards()*
- home_url()*
- Client ไม่ได้ล็อกอิน
- สืบจาก Person ตรง
- Lawyer
- +license_no
- Manager
- Admin
- Client
- +company

**พูด**

class diagram ฝั่งคน ลูกศรหัวสามเหลี่ยมทุกเส้นคือการสืบทอด ชี้ขึ้นหาคลาสแม่ Person เป็นคลาส abstract บนสุด มีชื่อ เลขบัตร และเบอร์โทร SystemUser สืบจาก Person และเพิ่ม username password และสถานะใช้งาน Lawyer Manager และ Admin สืบจาก SystemUser ส่วน Client ลูกความ สืบจาก Person ตรงๆ ไม่ผ่าน SystemUser เพราะลูกความไม่ได้ล็อกอินเข้าระบบ ไดอะแกรมนี้ตรงกับ domain/person.py ครับ

---

## หน้า 5 · Case เป็นศูนย์กลาง ถือการมอบหมาย นัด และโน้ต

**บนสไลด์**

- CLASS DIAGRAM ฝั่งคดีและตาราง (2/2) · หัวสามเหลี่ยม = สืบทอด · เส้นธรรมดา = ความสัมพันธ์
- CaseAssignment (−status)
- accept() · decline()
- Case (−status, −assignments)
- assign_lawyer() · advance_status()
- Schedule
- add() · find_conflicts()
- *
- หลายรายการ ต่อ 1 Lawyer (สไลด์ 4)
- ◇ ยืมลิสต์นัด
- *
- Appointment «abstract»
- reminder_lead_days()* · kind_label()*
- CaseNote · CaseEvent
- คดี 1 : * (ผูกด้วย case_id)
- «enum» · @dataclass
- CaseStatus 7 ค่า
- AssignmentStatus 4 ค่า
- Client
- ลูกความ 1 : คดี * (case.client)
- CourtHearing · ClientMeeting
- FilingDeadline
- นัดศาล 3 วัน · พบลูกความ 1 วัน · ยื่น 15 วัน
- Case 1 : * มอบหมาย / นัด / โน้ต
- Schedule ◇ นัด * (ยืมลิสต์นัดจาก repo มาตรวจ)

**พูด**

ฝั่งคดีและตาราง ตรงกลางคือ Case เก็บสถานะและรายการมอบหมายไว้เป็น private คดีหนึ่งมี CaseAssignment ได้หลายรายการ ซ้ายล่าง Appointment เป็นคลาส abstract มีลูกสามชนิด ขวามือ Schedule ไม่ได้สร้างนัดเอง แค่ยืมรายการนัดจาก repository มาตรวจนัดชน ฉบับเต็มที่มีเมธอดครบอยู่ในไฟล์สำรอง หน้า B7 ครับ

---

## หน้า 6 · คลาสแม่เป็น ABC: สร้างตรงไม่ได้ ลูกต้องเขียนเมธอดที่กำหนด

**บนสไลด์**

- ABSTRACTION · คลาสแม่กำหนดเมธอดที่ลูกต้องมี
- คลาสแม่บอกว่าลูกต้องมีเมธอดอะไร แต่ไม่บอกว่าทำยังไง

```
# domain/person.py:15,30
class Person(ABC):
    @abstractmethod
    def display_name(self): ...

class SystemUser(Person):
    @abstractmethod can_view_case()
    @abstractmethod dashboard_cards()
    @abstractmethod home_url()
```

```
# domain/appointment.py:29
class Appointment(ABC):
    @abstractmethod
    def reminder_lead_days(self): ...
    @abstractmethod
    def can_reschedule(self): ...
    @abstractmethod
    def kind_label(self): ...
```

- contact_info()/overlaps() เขียนที่แม่ครั้งเดียว ลูกทุกตัวใช้ร่วมกัน

```
Appointment(...)  →  TypeError:
Can't instantiate abstract class ...
```

- ผลที่ได้: สร้าง Appointment() ตรงๆ ไม่ได้ ต้องสร้างคลาสลูก

**พูด**

เริ่มหลัก OOP ข้อแรก Abstraction คลาสแม่ประกาศสัญญาด้วย ABC กับ abstractmethod ว่าลูกต้องมีเมธอดอะไรบ้าง ซ้ายคือ Person กับ SystemUser ที่บังคับให้ลูกมี display_name, can_view_case, dashboard_cards และ home_url ขวาคือ Appointment ที่บังคับ reminder_lead_days, can_reschedule และ kind_label ผลคือสร้าง Appointment ตรงๆ ไม่ได้ Python จะโยน TypeError ทันที ผู้เรียกจึงพึ่งแค่สัญญา ไม่ต้องรู้ว่าเป็นลูกตัวไหน ส่วนเมธอดที่ใช้ร่วมกันจริง เช่น contact_info กับ overlaps เขียนไว้ที่แม่ครั้งเดียว ไม่ต้องเขียนซ้ำในลูกครับ

---

## หน้า 7 · ลูกแต่ละคลาสเติม attribute และ display_name() ของตัวเอง

**บนสไลด์**

- INHERITANCE · ลูกได้ของจากแม่แล้วเติมของตัวเอง
- ลูกได้ทุกอย่างจากแม่ แล้วเติมของตัวเอง

| คลาส | ได้จากแม่ / เติมเอง |
|---|---|
| Person(ABC) | @abstractmethod display_name() |
| SystemUser(Person) | username · password_hash · is_active |
| Lawyer(SystemUser) | + license_no · display_name() → "ทนาย…" |
| Manager(SystemUser) | display_name() → "ผู้จัดการ…" |
| Admin(SystemUser) | display_name() → "ผู้ดูแลระบบ…" |
| Client(Person) | + company (ลูกความไม่ได้ล็อกอิน จึงสืบจาก Person ตรง) |

- ผลที่ได้: Lawyer มี name/phone โดยไม่ต้องเขียนซ้ำ · Client ไม่ใช่ SystemUser

**พูด**

Inheritance คลาสลูกได้ทุกอย่างจากแม่ แล้วเติมของตัวเอง Lawyer, Manager และ Admin ได้ username และ password จาก SystemUser แล้วแต่ละตัวเขียน display_name ของตัวเอง Lawyer ได้ทั้ง name phone จาก Person และ username password จาก SystemUser โดยไม่ต้องเขียนซ้ำ Lawyer เพิ่มแค่เลขใบอนุญาตว่าความ ส่วน Client สืบจาก Person ตรงๆ จุดที่อาจารย์มักถามคือ ทำไม Client ไม่สืบจาก SystemUser คำตอบคือลูกความไม่มี username และ password จึงไม่ผ่านความสัมพันธ์แบบ is-a กับผู้ใช้ระบบครับ

---

## หน้า 8 · เรียก home_url() ชื่อเดียว ได้หน้าแรกตามบทบาท

**บนสไลด์**

- POLYMORPHISM · เรียกเมธอดเดียว ได้พฤติกรรมตามชนิด
- เรียกเมธอดชื่อเดียว แต่ละคลาสตอบไม่เหมือนกัน

```
# domain/person.py:63,85,100
class Lawyer(SystemUser):
    def home_url(self) -> str:
        return "/schedule/today"
class Manager(SystemUser):
    def home_url(self) -> str:
        return "/manager/dashboard"
class Admin(SystemUser):
    def home_url(self) -> str:
        return "/admin/dashboard"
```

```
# api/routes/dashboard.py
return RedirectResponse(
    current_user.home_url())
```

- ผลที่ได้: home_url() บรรทัดเดียว ได้หน้าแรก 3 แบบ (ดูภาพหน้า 3)

**พูด**

Polymorphism คือเรียกเมธอดชื่อเดียว แต่ละคลาสตอบไม่เหมือนกัน ตัวอย่างคือ home_url ทนายไปหน้าตารางวันนี้ ผู้จัดการไปหน้า dashboard ของผู้จัดการ แอดมินไปหน้าแอดมิน route เรียกแค่ current_user.home_url() บรรทัดเดียว ไม่ต้องถามว่าเป็น role ไหน หน้าแรกสามแบบในสไลด์ 3 มาจากบรรทัดนี้ ส่วน reminder_lead_days ของนัดสามชนิดก็ใช้หลักเดียวกันครับ

---

## หน้า 9 · เปลี่ยนสถานะได้ผ่านเมธอดที่ตรวจกฎเท่านั้น

**บนสไลด์**

- ENCAPSULATION · แก้สถานะตรงจากข้างนอกไม่ได้
- ข้อมูลสำคัญแก้ได้ผ่านเมธอดที่ตรวจกฎเท่านั้น

```
# domain/case.py
_status: CaseStatus = field(...OPEN...)
@property
def status(self): ...
    # ไม่มี setter: แก้ตรงได้ AttributeError
def advance_status(self, ...):
    # ตรวจกฎก่อนเปลี่ยนสถานะ
    self._status = new_status
```

```
# domain/assignment.py
def accept(self):
    # ตรวจว่ายังรอตอบรับอยู่
    self._status = AssignmentStatus.ACCEPTED
```

- ข้อยกเว้น: repository ตั้ง _status ตอนโหลดแถวเดิมจาก DB (ผ่านกฎมาแล้วตอนบันทึก)
- ผลที่ได้: ข้ามขั้นไม่ได้ ปุ่มเสนอแค่ขั้นถัดไป "ตัดสิน"

**พูด**

Encapsulation สถานะของคดีกับสถานะการมอบหมายแก้ตรงจากข้างนอกไม่ได้ เก็บไว้ใน _status และเปิดให้อ่านผ่าน property status ที่ไม่มี setter ถ้าสั่ง case.status = ... จะได้ AttributeError การเปลี่ยนสถานะต้องผ่านเมธอดที่ตรวจกฎก่อน เช่น advance_status ต้องเลื่อนทีละขั้น และจะยื่นฟ้องได้ต้องมีทนายตอบรับแล้ว ถ้าผิดกฎจะโยน error กล่องล่างคือการมอบหมายใช้หลักเดียวกัน accept ตรวจก่อนว่ายังรอตอบรับอยู่ แล้วจึงเปลี่ยนเป็น ACCEPTED ภาพขวาบนคือหัวคดี ป้ายสถานะบอกว่าอยู่ขั้นสืบพยาน ภาพขวาล่างคือแผงจัดการคดี มีปุ่มม่วงปุ่มเดียวคือเลื่อนสถานะเป็นตัดสิน เพราะ advance_status ไม่ยอมให้ข้ามขั้น ข้อยกเว้นมีที่เดียวคือ repository ตั้ง _status ตรงตอนโหลดแถวเดิมจากฐาน ค่านั้นผ่านกฎมาแล้วตอนบันทึก จึงไม่ต้องตรวจซ้ำครับ

---

## หน้า 10 · DomainError กับลูก 4 ชนิด · api แปลเป็นข้อความไทย

**บนสไลด์**

- EXCEPTION HIERARCHY · แยก error ตามกลุ่มกฎ

```
DomainError (แม่)
├ ScheduleConflictError  นัดเวลาชนกัน
├ InvalidStatusTransition  ข้ามขั้นสถานะ
├ RescheduleNotAllowed  เลื่อนนัดไม่ได้
└ AssignmentError  มอบหมาย/รับคดีผิดกฎ
```

```
try: schedule.add(appt)
except ScheduleConflictError as e:
    → ฟอร์มเดิม + "นัดชน…"
```

```
except AssignmentError as e:
    → HTTP 409 "รับได้เฉพาะ…"
```

- ตัวอย่างจริง: เพิ่มนัดเวลาชน → ScheduleConflictError → ข้อความนี้
- ทำผิดกฎ → โยน error ชนิดเฉพาะ → หน้าเว็บแสดงข้อความไทย

**พูด**

error ทุกตัวในระบบเป็นคลาส แม่คือ DomainError มีลูกสี่ตัวตามชนิดความผิด คือนัดเวลาชนกัน ข้ามขั้นสถานะ เลื่อนนัดไม่ได้ และมอบหมายหรือรับคดีผิดกฎ ตัวอย่างจริงอยู่กลางสไลด์ ผมกรอกนัดพบลูกความทับเวลานัดเดิมของทนายคนเดียวกัน ระบบโยน ScheduleConflictError แล้ว route ที่จับ error ชนิดนี้ไว้จะแสดงฟอร์มเดิมพร้อมแถบแดง ไม่บันทึกนัดนั้น สรุปคือทำผิดกฎแล้วได้ error ชนิดเฉพาะ และหน้าเว็บแปลเป็นข้อความไทยครับ (ถ้าถูกถาม: รหัสกฎคือ BR-1, BR-7 8 9 18, BR-3 กับ 5 และ BR-15 ถึง 19 ไม่มี handler กลาง แต่ละ route จับ subclass ของตัวเอง และเทส assert ชนิด subclass ที่เจาะจง)

---

## หน้า 11 · เส้นทางคดีจากเปิดถึงปิด และทางแยกเมื่อทนายขอถอนตัว

**บนสไลด์**

- FLOW ของคดี
- เปิดคดี
- มอบหมายทนาย
- รับ / ปฏิเสธ
- นัด + เลื่อนสถานะ
- ปิดคดี
- ขอถอนตัว
- อนุมัติ / ไม่อนุมัติ
- ย้าย / ยกเลิกนัด
- กล่องแดง =
- ทางแยกถอนตัว
- เส้นทึบ = ทางหลัก · เส้นประแดง = ทางแยกถอนตัว
- ปิดคดีได้เมื่อไม่มีนัดในอนาคตหรือกำหนดยื่นค้าง

**พูด**

flow ของคดีตั้งแต่เปิดจนปิด ขั้นหลักทั้งห้าขั้นมีเมธอดใน domain คุมกฎ ผู้จัดการเปิดคดี มอบหมายทนายด้วย assign_lawyer ทนายตอบรับหรือปฏิเสธด้วย accept หรือ decline จากนั้นเพิ่มนัดและเลื่อนสถานะคดี จนปิดคดีได้เมื่อ can_close เป็นจริง คือไม่มีนัดหรือกำหนดยื่นค้าง ทางแยกสีแดงคือการถอนตัว ทนายขอถอนตัว ผู้จัดการอนุมัติหรือไม่อนุมัติ ถ้าอนุมัติก็ย้ายหรือยกเลิกนัด ขั้นย้ายและยกเลิกนัดเป็นงานของ AppointmentRepository โดยตรง ไม่มีกฎใน domain คุม ถ้าถามชื่อเมธอด ขั้นหลักคือ Case กับ repo.add assign_lawyer accept decline add advance_status can_close ส่วนทางแยกคือ request_withdraw approve reject_withdraw reassign cancel ครับ

---

## หน้า 12 · สรุป 4 หลัก OOP และงานต่อยอด

**บนสไลด์**

| หลัก | ในระบบนี้ |
|---|---|
| Encapsulation | Case._status / CaseAssignment._status อ่านอย่างเดียว เปลี่ยนผ่านเมธอด |
| Abstraction | Person / SystemUser / Appointment ประกาศสัญญา ลูกต้องเติม |
| Inheritance | Lawyer/Manager/Admin สืบ SystemUser · นัด 3 ชนิดสืบ Appointment |
| Polymorphism | home_url() บรรทัดเดียว ได้หน้าแรก 3 แบบ ไม่ถามชนิด |
| Exception | ทำผิดกฎ → error ชนิดเฉพาะ → ข้อความไทย |

- เทส: 90 เทสผ่านทั้งหมด · domain เทสโดยไม่ใช้ DB · repository เทสบนฐานแยก
- ต่อยอด: แจ้งเตือนทางอีเมล/ไลน์ · ซิงก์ปฏิทิน · สิทธิ์ละเอียดต่อคดี (ตอนนี้ manager เห็นหมด)
- กฎธุรกิจทั้งหมดอยู่ในเมธอดของคลาสใน domain/

**พูด**

สรุป สี่หลักของ OOP กับการจัดการ error ที่โชว์ในระบบนี้ Encapsulation สถานะคดีและการมอบหมายอ่านได้อย่างเดียว เปลี่ยนผ่านเมธอดที่ตรวจกฎ Abstraction Person SystemUser และ Appointment ประกาศสัญญาให้ลูกเติม Inheritance ผู้ใช้สามบทบาทสืบจาก SystemUser และนัดสามชนิดสืบจาก Appointment ซึ่งเป็น is-a จริง Polymorphism home_url บรรทัดเดียวพาผู้ใช้ไปหน้าแรกตามบทบาท และ Exception ทำผิดกฎแล้วได้ error ชนิดเฉพาะที่หน้าเว็บแปลเป็นข้อความไทย งานต่อยอดคือแจ้งเตือนทางอีเมลหรือไลน์ ซิงก์ปฏิทิน และสิทธิ์ละเอียดต่อคดี กฎทั้งหมดนี้มีเทสคุม 90 เทส ผ่านทั้งหมด กฎธุรกิจทั้งหมดอยู่ในเมธอดของคลาสใน domain ครับ

---

## หน้า 13 · จบการนำเสนอ

**บนสไลด์**

- ขอบคุณครับ
- นายเมทนี พูลสมบัติ · รหัสนักศึกษา 6821500060

**พูด**

ขอบคุณครับ เปิดรับคำถามครับ

---

# สไลด์สำรอง (เปิดเมื่อถูกถาม)

---

## หน้า Q&A · คำถามที่อาจถูกถาม

**บนสไลด์**

- สไลด์สำรอง เปิดเมื่อถูกถาม

**_status ยังเขียนทับได้ไหม?**

- ได้ Python ไม่มี private จริง · _ คือข้อตกลง · property ไม่มี setter กันการแก้ผ่าน .status · ต้องการมากขึ้นใช้ __status (name mangling)

**ทำไมไม่มี interface?**

- Python ไม่มีคีย์เวิร์ด interface · ใช้ ABC + @abstractmethod ทำหน้าที่เดียวกัน

**มี overloading ไหม?**

- Python ไม่มี method overloading แบบ Java · ระบบนี้ใช้ overriding (เช่น home_url)

**composition vs aggregation?**

- Case ถือ CaseAssignment เป็นของตัวเอง = composition · Schedule ยืมลิสต์นัดจาก repo = aggregation

**พูด**

สไลด์สำรองสำหรับตอบคำถาม เปิดเฉพาะเมื่อถูกถาม ถ้าถามว่า _status ยังเขียนทับได้ไหม ตอบตรงๆ ว่าได้ เพราะ Python ไม่มี private จริง ขีดล่างหนึ่งตัวเป็นข้อตกลงว่าห้ามแตะ สิ่งที่กันจริงคือ property ที่ไม่มี setter ถ้าต้องการกันมากขึ้นใช้ขีดล่างสองตัวให้เกิด name mangling ได้ ถ้าถามว่าทำไมไม่มี interface ตอบว่า Python ไม่มีคีย์เวิร์ด interface ใช้ ABC กับ abstractmethod ทำหน้าที่เดียวกัน ถ้าถามเรื่อง overloading ตอบว่า Python ไม่มี method overloading แบบ Java ระบบนี้ใช้ overriding แทน และถ้าถามเรื่อง composition กับ aggregation Case ถือ CaseAssignment ไว้เป็นของตัวเองคือ composition ส่วน Schedule แค่ยืมรายการนัดมาตรวจ ไม่ได้เป็นเจ้าของ คือ aggregation ครับ

---

## หน้า B1 · dependency ไปทางเดียว: domain ไม่ import ชั้นอื่น

**บนสไลด์**

- สถาปัตยกรรม 3 ชั้น
- api/ (web)
- routes/ · deps.py · auth.py
- 39 routes · Depends(get_db)
- repository/ (persistence)
- Repository class ต่อตาราง + db.py
- map แถว ↔ object
- domain/ (business objects)
- กฎ BR-* ทั้งหมดอยู่ที่นี่
- import ได้แค่ stdlib + กันเอง
- api → repository, domain
- repository → domain
- domain → ไม่มีใคร (กฎ)
- ตรวจกฎได้: grep -r "from api\|from repository" domain/ ต้องว่างเปล่า (ตอนนี้ 0 บรรทัด)
- DB เปิด/ปิดที่จุดเดียว: get_db ใน api/deps.py ผ่าน Depends

**พูด**

โค้ดแบ่งเป็นสามชั้น ชั้น api ดูแลหน้าเว็บ ชั้น repository คุยกับฐานข้อมูล และชั้น domain เก็บกติกาธุรกิจทั้งหมด กฎสำคัญคือการพึ่งพาไปทางเดียว api เรียก repository และ domain ได้ repository เรียก domain ได้ แต่ domain ไม่ import ใครเลย กฎนี้ตรวจได้จริงด้วยคำสั่ง grep ใน domain ต้องไม่เจอ from api หรือ from repository ซึ่งตอนนี้ผลเป็นศูนย์บรรทัด ส่วนการเปิดปิดการเชื่อมต่อฐานข้อมูลอยู่จุดเดียวคือ get_db ใน api/deps.py ที่ส่งเข้า route ผ่าน Depends ครับ

---

## หน้า B2 · แต่ละโฟลเดอร์มีหน้าที่เดียว

**บนสไลด์**

- โครงโฟลเดอร์

| โฟลเดอร์ | หน้าที่ |
|---|---|
| domain/ | กติกาธุรกิจ: Person, Case, Appointment, Schedule, CaseAssignment, … |
| repository/ | Repository class ต่อตาราง คุย MariaDB ตรงๆ ไม่ใช้ ORM |
| api/ | main.py factory บางๆ · deps.py ของใช้ร่วม · routes/ · auth.py |
| templates/ · static/ | Jinja2 (Pico.css + HTMX) · theme.css |
| db/ | schema.sql · seed.sql · migrations/ |
| tools/ · tests/ | generate_seed.py สร้าง seed · pytest 90 เทส |
| docs/ | proposal · backlog · uml · slides |

- api/main.py 1,212 → 23 บรรทัด  ·  routes/ 7 โมดูล 39 routes

**พูด**

โครงโฟลเดอร์ตั้งใจให้แต่ละโฟลเดอร์มีหน้าที่เดียว domain คือกติกาธุรกิจ repository คือ SQL api คือ route ของหน้าเว็บ templates คือหน้าตา db เก็บ schema กับ seed และ tests เก็บเทสทั้งหมด api/main.py เดิมยาว 1,212 บรรทัด หลัง refactor เหลือ 23 บรรทัด เพราะแยก route ออกเป็น 7 โมดูล ถ้าถามว่าแยกทำไม คำตอบคือให้คนอ่านเดาได้ว่าโค้ดอยู่ไหนโดยไม่ต้องเปิดหาครับ

---

## หน้า B3 · SQL ทั้งหมดอยู่ใน repository/ · กฎทั้งหมดอยู่ใน domain/

**บนสไลด์**

- REPOSITORY PATTERN · Repository class ต่อตาราง

```
cases = CaseRepository(conn)        # ถือ connection ไว้หนึ่งตัว
case = cases.get_by_id(case_id)     # คืน object ไม่ใช่ dict/row
```

```
_ROLE_TO_CLASS = {"lawyer": Lawyer, "manager": Manager, "admin": Admin}
cls = _ROLE_TO_CLASS[row["role"]]   # อ่าน role แล้วสร้างให้ตรงคลาสลูก
```

```
# repository/case_repo.py: peer repo ใช้ connection เดียวกัน
def __init__(self, conn, clients=None, users=None):
    self._conn = conn
    self._clients = clients or ClientRepository(conn)
```

- ทำไมไม่ใช้ ORM: โปรเจกต์เล็ก SQL ตรงๆ อ่านง่ายกว่า
- ย้ายฐานข้อมูล: แก้ที่ repository/ ที่เดียว

**พูด**

Repository pattern SQL ทั้งหมดอยู่ใน repository ที่เดียว domain ไม่เคยเห็น SQL และ repository ไม่รู้จักกฎธุรกิจ แต่ละตารางมีคลาสของตัวเอง เช่น CaseRepository ถือ connection ไว้หนึ่งตัว และคืนค่าเป็น object ของ domain ตัวอย่างที่สอง UserRepository อ่านคอลัมน์ role แล้วสร้าง object ให้ตรงคลาสลูก Lawyer Manager หรือ Admin ถ้าถามว่าทำไมไม่ใช้ ORM ตอบว่าโปรเจกต์ขนาดนี้ SQL ตรงๆ อ่านง่ายกว่า และถ้าวันหนึ่งย้ายฐานข้อมูล ก็แก้แค่ repository ครับ

---

## หน้า B4 · flow เดียวกันบนหน้าจอจริง

**บนสไลด์**

- มอบหมาย → รับ / ปฏิเสธ → จัดการคดี
- 1. มอบหมายทนาย
- 2. รับ / ปฏิเสธ
- 3. นัด · เลื่อนสถานะ · ขอถอนตัว
- ผู้จัดการเห็นภาระงานทุกคนก่อนเลือก
- popup คดีรอตอบรับ: accept() · decline()
- หน้าคดีหลังทนายรับงาน
- ภาพจาก http://localhost:8000 (ข้อมูล seed) · manager1 และ lawyer1

**พูด**

สไลด์นี้คือ flow เดียวกันบนหน้าจอจริง ซ้ายคือหน้ามอบหมายของผู้จัดการ เรียงทนายจากภาระงานน้อยไปมาก คนที่งานเกินจะมีป้ายเตือน ผู้จัดการจึงเลือกคนที่ว่างกว่าได้ทันที กลางคือ popup คดีรอตอบรับของทนาย มีปุ่มรับคดีกับปฏิเสธ ซึ่งเรียก accept และ decline ขวาคือหน้าคดีหลังทนายรับแล้ว มีตารางนัด ปุ่มเลื่อนสถานะ และปุ่มขอถอนตัวจากคดี ซึ่งเป็นจุดเริ่มของทางแยกสีแดงในสไลด์ flow คดีครับ

---

## หน้า B5 · 90 เทส: domain เทสโดยไม่ใช้ DB · เทส DB ใช้ฐานแยก

**บนสไลด์**

- TESTING · เคยล้างฐานจริงมาแล้วหนึ่งครั้ง

| ไฟล์ | จำนวน | ไฟล์ | จำนวน |
|---|---|---|---|
| appointment | 10 | assignment | 19 |
| case | 19 | person | 8 |
| schedule | 12 | auth | 6 |
| repository | 12 | db_safety | 4 |
| รวม |  |  | 90 |

- บทเรียนจริง
- fixture เคย TRUNCATE ฐาน lawfirm-db ของแอป
- ตอนนี้เทสใช้ lawfirm_test สร้าง + ลง schema เอง
- guard pytest.fail ก่อน TRUNCATE ถ้าชื่อชน
- repository 12 เทสวิ่งบนฐานแยก · db_safety 4 เทสตรวจ guard โดยไม่ต้องใช้ DB

**พูด**

การทดสอบมี 90 เทส แบ่งตามไฟล์ตามตาราง ส่วนใหญ่ทดสอบชั้น domain ซึ่งไม่ต้องใช้ฐานข้อมูลเลย เทส repository 12 เทสวิ่งบนฐานข้อมูลแยกชื่อ lawfirm_test ตอนแรก fixture ของเทสสั่ง TRUNCATE ฐาน lawfirm-db ของแอปตัวจริง ทำให้ข้อมูลหายไปครั้งหนึ่ง ตอนนี้แก้แล้ว เทสสร้างฐาน lawfirm_test ลง schema ให้เอง และมี guard ที่สั่ง pytest.fail ก่อน TRUNCATE ถ้าชื่อฐานชนกับของจริง และมีเทส guard อีก 4 เคสที่ไม่ต้องใช้ฐานข้อมูล คอยกันไม่ให้เกิดซ้ำครับ

---

## หน้า B6 · Demo 3 ฉาก: ทนาย ผู้จัดการ แอดมิน

**บนสไลด์**

- DEMO SCRIPT · http://localhost:8000 · ทุกบัญชีใช้รหัส password123

**lawyer1**

- 1. เปิด popup "คดีรอตอบรับ"
- 2. กดรับคดี
- 3. "+ เพิ่มนัด" นัดศาลพรุ่งนี้
- 4. ดูแผงใกล้ครบกำหนด

**manager1**

- 1. ดูคิว "ยังไม่มีทนายตอบรับ"
- 2. กดมอบหมาย
- 3. เปิดคำขอถอนตัว
- 4. อนุมัติพร้อมย้ายนัด

**admin**

- 1. "+ เพิ่มผู้ใช้ใหม่"
- 2. สร้างทนาย
- 3. ปิดใช้งาน
- 4. เปิดคืน
- เวลาน้อย: เล่นแค่ฉาก lawyer1 (รับคดี + เพิ่มนัด) ก็เห็น loop หลักครบ

**พูด**

ถ้าอาจารย์ขอดู demo มีสามฉาก ทุกบัญชีใช้รหัสผ่าน password123 ฉากแรก lawyer1 เปิด popup คดีรอตอบรับ กดรับคดี แล้วเพิ่มนัดศาลพรุ่งนี้ จากนั้นดูแผงรายการใกล้ครบกำหนด ฉากสอง manager1 ดูคิวคดีที่ยังไม่มีทนายตอบรับ กดมอบหมาย แล้วเปิดคำขอถอนตัว กดอนุมัติพร้อมย้ายนัด ฉากสาม admin เพิ่มผู้ใช้ใหม่เป็นทนาย ปิดใช้งาน แล้วเปิดคืน ถ้าเวลาน้อย จะเล่นแค่ฉากทนาย คือรับคดีกับเพิ่มนัด ก็เห็น loop หลักของระบบครบครับ

---

## หน้า B7 · Case เป็นศูนย์กลาง ถือการมอบหมาย นัด และโน้ต (ฉบับเต็ม)

**บนสไลด์**

- CLASS DIAGRAM ฉบับเต็ม · สำรอง
- CaseAssignment (−status)
- accept() · decline()
- request_withdraw() · approve/reject()
- Case (−status, −assignments)
- assign_lawyer() · advance_status()
- lawyers() · lead_lawyer() · can_close()
- Schedule
- add() · find_conflicts()
- day/week/month_view() · mark_done()
- *
- หลายรายการ ต่อ 1 Lawyer (สไลด์ 4)
- ◇ ยืมลิสต์นัด
- *
- Appointment «abstract»
- reminder_lead_days()* · kind_label()*
- can_reschedule()* · overlaps()
- reschedule() · cancel() · is_due_soon()
- CaseNote · CaseEvent
- คดี 1 : * (ผูกด้วย case_id)
- validate_text() · can_modify()
- «enum» · @dataclass
- CaseStatus 7 ค่า
- AssignmentStatus 4 ค่า
- domain ทุกคลาสเป็น @dataclass
- Client
- ลูกความ 1 : คดี * (case.client)
- CourtHearing · ClientMeeting
- FilingDeadline
- นัดศาล 3 วัน · พบลูกความ 1 วัน · ยื่น 15 วัน
- Case 1 : * มอบหมาย / นัด / โน้ต
- Schedule ◇ นัด * (ยืมลิสต์นัดจาก repo มาตรวจ)

**พูด**

ฝั่งคดีและตาราง ตรงกลางคือ Case เก็บสถานะและรายการมอบหมายไว้เป็น private คดีหนึ่งมี CaseAssignment ได้หลายรายการ แต่ละรายการผูกกับทนายหนึ่งคน ซ้ายล่างคือ Appointment เป็นคลาส abstract มีลูกสามชนิด นัดศาล นัดพบลูกความ และกำหนดยื่นเอกสาร นัดศาลเตือนล่วงหน้า 3 วัน นัดพบลูกความ 1 วัน กำหนดยื่น 15 วัน ตัวเลขต่างกันแต่เรียกเมธอดเดียวกัน ขวามือคือ Schedule ไม่ได้สร้างนัดเอง แค่ยืมรายการนัดจาก repository มาตรวจนัดชน เป็นความสัมพันธ์แบบ aggregation และทุกคลาสใน domain เขียนเป็น dataclass ส่วนสถานะคดีกับสถานะการมอบหมายเป็น enum ครับ
