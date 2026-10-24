Updated: 2026-10-24

# HANDOFF — Law Firm Project (งาน OOP ส่งอาจารย์)

## Goal

เตรียมโปรเจกต์ระบบผู้ช่วยจัดการคดีและนัดหมายสำหรับทนายความ (FastAPI + Jinja2 + MariaDB) ให้นำเสนออาจารย์ได้ในฐานะงาน **OOP**
- โค้ดเป็นระเบียบ แยก folder ตามหน้าที่ อธิบายได้
- UI สม่ำเสมอตาม `DESIGN.md`
- สไลด์ .pptx นำเสนอ 10 นาที ผู้ฟังหลักคือเพื่อนที่เพิ่งเรียน OOP (อาจารย์ให้คะแนน) เน้น 4 หลัก OOP ทุกข้ออ้างชี้ไปโค้ดจริง

## Current Progress

สถานะ: master = `f4a786c` push แล้วที่ `https://github.com/Maythane/Law-Firm-Project` (remote `origin`, branch `master`) · pytest **90 passed** (`'.venv/bin/python' -m pytest -q`, ต้องเปิด Docker)

### Slides .pptx (เสร็จ, commit แล้ว)
- ตัวสร้าง: `docs/slides/build_presentation.py` (python-pptx, ธีมมืด, Sarabun, accent `#B39DDB`) รันครั้งเดียวได้ 2 ไฟล์
  - `docs/slides/LawFirm_Presentation.pptx` — 12 หน้าที่นำเสนอจริง: ปก · ปัญหา · ระบบ+ภาพ 3 role · class diagram คน · class diagram คดี (ฉบับย่อ) · Abstraction · Inheritance · Polymorphism (`home_url()` อย่างเดียว) · Encapsulation · Exception · flow คดี · สรุป
  - `docs/slides/LawFirm_Presentation_Backup.pptx` — 8 หน้าสำรอง: Q&A · B1 dependency · B2 folders · B3 Repository · B4 flow บนหน้าจอ · B5 Testing · B6 Demo · B7 class diagram คดีฉบับเต็ม
- ลำดับหน้ากำหนดที่ `ORDER` / `LABEL` ใกล้ `title()`; เลขมุมขวาบน 1–12, Q&A ไม่มีเลข, สำรอง B1–B7
- หน้า OOP 6–9 ใช้โครงเดียวกัน: นิยามภาษาไทย 1 บรรทัด → โค้ด (บรรทัดสำคัญขึ้นต้น `!` ใน `code()` = สี accent) → แถบม่วง "ผลที่ได้"
- รหัส BR-xx และชื่อเมธอดของ flow ไม่อยู่บนสไลด์หลัก ย้ายไปใน notes (ส่วน "ถ้าถูกถาม")
- speaker notes ภาษาไทยครบทุกหน้า ตรวจแล้วว่าตรงกับสไลด์ (commit `f4a786c`)
- ภาพหน้าจอจริงใน `docs/slides/assets/` (ข้อมูล seed, ถ่าย 2x ด้วย Playwright): `lawyer_today`, `manager_dashboard`, `admin_dashboard`, `admin_users`, `manager_assign`, `pending_dialog`, `case_detail`, `case_status_head`, `case_status_panel`, `schedule_conflict`
- overwrite guard: แต่ละไฟล์มี stamp `.LawFirm_Presentation*.pptx.sha256` ถ้าแก้ pptx ด้วยมือ สคริปต์จะไม่ทับ (ต้อง `--force` ซึ่งสำรองเป็น `.pptx.bak`) — ห้ามใส่ `--force` เอง
- `docs/slides/index.html` (HTML 17 หน้า) ยังอยู่ แต่ไม่ได้ใช้นำเสนอแล้ว

### UI / Refactor / Test DB (เสร็จก่อนหน้า)
- design review High/Medium แก้แล้ว ข้อ Low ตั้งใจข้าม
- refactor: `api/main.py` 23 บรรทัด, routes แยก 7 โมดูล, repository เป็นคลาส, `SystemUser.home_url()` polymorphic, `_status` + read-only property, ลบ `domain/firm.py`
- เทส DB ใช้ฐานแยก `lawfirm_test` + guard `pytest.fail` ก่อน TRUNCATE (`repository/db.py`, `tests/test_db_safety.py`)

### Orca
- workspace ลูก `muse-task` (child ของ folder `OOP:AML`) มี Muse Code รันอยู่ terminal เดียว ใช้ทำงานแก้สไลด์
- worktree ลูก `nautilus` ที่ `/Users/mark/orca/workspaces/Law Firm Project/nautilus` (branch merge แล้ว)
- `orca.yaml` (แชร์ `.venv` ให้ worktree ลูก) — ผู้ใช้ให้เก็บไว้

## What Worked

- แก้สไลด์ = แก้ `build_presentation.py` → รันด้วย Python ที่มี python-pptx 1.0.2 → `app.open` ใน DeckCraft (`--control 47811`) → `ui.render` แล้วดู PNG ทุกหน้าที่เปลี่ยน
- สั่ง muse: เขียนโจทย์ยาวเป็นไฟล์ markdown แล้ว `orca terminal send --terminal <handle> --text "อ่านและทำตาม <path>" --enter --json`
- อ่านผล muse: TUI ของ Muse Code วาดทับ `terminal read` อ่านคำตอบไม่ได้ → สั่งให้เขียนรายงานลงไฟล์ (`.../scratchpad/lf/muse_report.md`) แล้วรอด้วย loop `terminal wait --for tui-idle` + เช็คไฟล์
- ตรวจงาน muse เองทุกครั้ง: muse เคยรายงานว่า "ไม่ทับ" แต่ภาพนัดชนหน้า 10 ล้นใต้แถบม่วงจริง
- ถ่ายภาพหน้าจอ: Playwright context ใหม่ viewport 1100x700 `deviceScaleFactor: 2`, login ด้วย `ctx.request.post('/login', {form})`, ถ่ายเฉพาะ element (`main`, `aside.case-side > .panel`, `.page-head`) อ่านได้ดีกว่าทั้งหน้า
- ภาพนัดชนได้จากการส่งฟอร์ม `/schedule/new` ทับเวลานัดเดิมของ lawyer1 — ระบบปฏิเสธ ไม่เขียน DB
- commit: แตก branch ชั่วคราว → commit → `git merge --ff-only` เข้า master → push → ลบ branch
- ตรวจ refactor ไม่เปลี่ยนพฤติกรรม: รันแอปเก่า/ใหม่คนละพอร์ตแล้ว crawl ทุกหน้า GET เทียบ HTML

## What Didn't Work

- **pytest เคยล้างฐานแอปจริง** — แก้แล้วด้วย `lawfirm_test` + guard; อย่าย้อนกลับ
- ภาพหน้าจอแบบทั้งหน้าย่อลงสไลด์แล้วอ่านไม่ออก → ใช้ภาพเฉพาะ element
- DeckCraft 0.8.0: ไม่มีฟอนต์ emoji สี, ตัดคำไทยกลางคำในกล่องแคบ, พิมพ์ไทยในช่อง Notes แล้วสระหาย (ตั้ง notes ผ่านสคริปต์เท่านั้น)
- venv อยู่ใน path ที่มี `:` (`OOP:AML`) ไม่ได้ — venv ของ python-pptx อยู่ใน scratchpad ซึ่งถูกล้างเมื่อผ่านหลายวัน; ถ้าหาย สร้างใหม่: `python3 -m venv <dir> && <dir>/bin/pip install python-pptx==1.0.2 pillow`
- auto mode ปฏิเสธคำสั่ง mass delete (TRUNCATE+import seed) — ให้ผู้ใช้รันเองด้วย `! <command>`
- muse ใน worktree ลูกเคยรัน `docker compose up -d db` เองจนชนพอร์ต 3306 — บอก muse ให้ใช้ DB ของ stack หลัก

## Next Steps

1. ซ้อมพูด 12 หน้าให้ได้ ~10 นาที (อ่านจาก notes) เปิดไฟล์ backup ไว้อีกหน้าต่างสำหรับตอบคำถาม
2. demo สดไม่จำเป็น (ใช้ภาพในสไลด์) ถ้าอาจารย์ขอ: `docker compose up -d` แล้วเปิด http://localhost:8000 (`password123`: `admin`, `manager1`, `lawyer1`–`lawyer8`) ตามหน้า B6
3. ข้อความในแอปยังมีรหัสกฎท้ายข้อความ เช่น "(BR-1)" ในแถบแดงนัดชน — ไม่ได้แก้ (เป็นโค้ดแอป) ถ้าอยากเอาออกต้องแก้ข้อความ error ใน `domain/`
4. ข้อ Low ใน design review ยังไม่ทำ — ทำต่อถ้าผู้ใช้ต้องการ
5. ถ้าไม่ใช้ worktree `nautilus` แล้ว: `orca worktree rm --worktree "path:/Users/mark/orca/workspaces/Law Firm Project/nautilus" --json`
6. `mockup/dashboard.html` และ `docs/slides/index.html` — ผู้ใช้ยังไม่ตัดสินว่าจะเก็บไว้หรือเอาออก
