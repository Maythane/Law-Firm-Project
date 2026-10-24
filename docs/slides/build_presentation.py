"""Generate LawFirm_Presentation.pptx (dark theme, Thai, Sarabun) from the
content of docs/slides/index.html, with Thai speaker notes.

Run: python build_presentation.py [--force]  (needs python-pptx)
Refuses to overwrite the pptx if it was edited after the last build
(e.g. saved from DeckCraft or PowerPoint). --force backs it up to .bak and overwrites.
"""
import hashlib
import shutil
import sys
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Pt

HERE = Path(__file__).parent
ASSETS = HERE / "assets"  # screenshots of the running app (localhost:8000)
OUT_MAIN = HERE / "LawFirm_Presentation.pptx"  # 12 main slides (ORDER[:12])
OUT_BACKUP = HERE / "LawFirm_Presentation_Backup.pptx"  # Q&A + B1..B6 (ORDER[12:])
OUT = OUT_MAIN
STAMP_MAIN = HERE / ".LawFirm_Presentation.pptx.sha256"  # hash of the last generated file
STAMP_BACKUP = HERE / ".LawFirm_Presentation_Backup.pptx.sha256"
STAMP = STAMP_MAIN

FONT = "Sarabun"
MONO = "Menlo"
BG = RGBColor(0x1E, 0x1E, 0x1E)
PANEL = RGBColor(0x2B, 0x2B, 0x2B)
CODE_BG = RGBColor(0x16, 0x16, 0x16)
HILITE = RGBColor(0x36, 0x2D, 0x4A)  # dark lavender fill for key classes
LINE = RGBColor(0x44, 0x44, 0x44)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0xA6, 0xA6, 0xA6)
BLACK = RGBColor(0x00, 0x00, 0x00)
ACCENT = RGBColor(0xB3, 0x9D, 0xDB)  # project lavender, readable on dark
RED = RGBColor(0xFF, 0x8A, 0x80)
RED_BG = RGBColor(0x45, 0x26, 0x24)

W, H = 960, 540  # slide size in pt (16:9)

prs = Presentation()
prs.slide_width = Pt(W)
prs.slide_height = Pt(H)
BLANK = prs.slide_layouts[6]


def set_font(run, size, bold=False, color=WHITE, mono=False):
    """Latin font plus Sarabun for east-asian and complex-script (Thai) glyphs."""
    f = run.font
    f.name = MONO if mono else FONT
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", FONT)


def new_slide(notes):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    s.notes_slide.notes_text_frame.text = notes
    return s


def rect(s, x, y, w, h, fill=PANEL, line=None):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Pt(x), Pt(y), Pt(w), Pt(h))
    r.fill.solid()
    r.fill.fore_color.rgb = fill
    if line:
        r.line.color.rgb = line
        r.line.width = Pt(1.25)
    else:
        r.line.fill.background()
    r.shadow.inherit = False
    return r


def text(s, x, y, w, h, lines, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=6, mono=False):
    """lines: str or list of str / (str, dict) where dict overrides size/color/bold."""
    tb = s.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(4)
    tf.margin_top = tf.margin_bottom = Pt(2)
    if isinstance(lines, str):
        lines = [lines]
    for i, item in enumerate(lines):
        t, o = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = o.get("align", align)
        p.space_after = Pt(spacing)
        r = p.add_run()
        r.text = t
        set_font(r, o.get("size", size), o.get("bold", bold), o.get("color", color), mono)
    return tb


# presentation order: 12 main slides, Q&A, then backup slides (B7 = full case diagram)
ORDER = [1, 2, 3, 6, 7, 8, 9, 10, 11, 13, 14, 18, 19, 4, 5, 12, 15, 16, 17, 20]
LABEL = {old: str(new) for new, old in enumerate(ORDER[:12], 1)}
LABEL.update({old: f"B{i}" for i, old in enumerate(ORDER[13:], 1)})


def title(s, t, sub=None, num=None):
    text(s, 40, 26, 820, 44, t, size=28, bold=True)
    if sub:
        text(s, 40, 68, 860, 26, sub, size=15, color=MUTED)
    rect(s, 40, 102, 880, 1.5, fill=LINE)
    rect(s, 40, 101, 80, 3, fill=ACCENT)
    if num:
        text(s, 860, 28, 60, 30, LABEL.get(num, ""), size=14, color=MUTED, align=PP_ALIGN.RIGHT)


def caption(s, x, y, w, t):
    text(s, x, y, w, 22, t, size=12, color=MUTED)


def image(s, name, x, y, w, h, crop=(0, 0, 0, 0)):
    """Fit a screenshot into box (x, y, w, h), keep aspect ratio, centre it.
    crop = fractions trimmed from (left, top, right, bottom)."""
    iw, ih = Image.open(ASSETS / name).size
    l, t, r, b = crop
    cw, ch = iw * (1 - l - r), ih * (1 - t - b)
    scale = min(w / cw, h / ch)
    dw, dh = cw * scale, ch * scale
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    rect(s, dx - 1.5, dy - 1.5, dw + 3, dh + 3, fill=LINE)
    pic = s.shapes.add_picture(str(ASSETS / name), Pt(dx), Pt(dy), Pt(dw), Pt(dh))
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = l, t, r, b
    return dx, dy, dw, dh


def code(s, x, y, w, h, lines, size=13):
    """Monospace block; # lines muted; ! prefix marks a key line (ACCENT, ! stripped)."""
    rect(s, x, y, w, h, fill=CODE_BG, line=LINE)
    styled = []
    for ln in lines:
        stripped = ln.lstrip()
        if stripped.startswith("#"):
            styled.append((ln, {"color": MUTED}))
        elif stripped.startswith("!"):
            i = ln.find("!")
            styled.append((ln[:i] + ln[i + 1:], {"color": ACCENT, "bold": True}))
        else:
            styled.append(ln)
    text(s, x + 10, y + 8, w - 20, h - 16, styled, size=size, spacing=2, mono=True)


def result_bar(s, y, t, h=40, size=16):
    """Small 'ผลที่ได้' box near the bottom."""
    rect(s, 40, y, 880, h, fill=HILITE)
    text(s, 50, y + 4, 860, h - 8, t, size=size, bold=True, anchor=MSO_ANCHOR.MIDDLE,
         align=PP_ALIGN.CENTER)


def defn(s, t):
    """One plain-Thai definition line under the title bar."""
    text(s, 40, 108, 880, 30, t, size=18, color=ACCENT, bold=True)


def panel(s, x, y, w, h, head, lines, size=17, spacing=10):
    rect(s, x, y, w, h, fill=PANEL, line=LINE)
    text(s, x + 18, y + 14, w - 36, 30, head, size=20, bold=True, color=ACCENT)
    text(s, x + 18, y + 54, w - 36, h - 62, lines, size=size, spacing=spacing)


def box(s, x, y, w, h, lines, fill=PANEL, line=LINE, size=14):
    """Diagram box: first line bold, rest normal; centred."""
    rect(s, x, y, w, h, fill=fill, line=line)
    styled = [(lines[0], {"bold": True, "size": size + 2})] + list(lines[1:])
    text(s, x + 4, y + 4, w - 8, h - 8, styled, size=size, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, spacing=1)


def line(s, x1, y1, x2, y2, color=ACCENT, head=None, dash=False, width=1.5):
    """Straight connector; head = 'triangle' (inheritance) or 'arrow' at the end point."""
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Pt(x1), Pt(y1), Pt(x2), Pt(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    if dash:
        d = ln.makeelement(qn("a:prstDash"), {"val": "dash"})
        ln.append(d)
    if head:
        e = ln.makeelement(qn("a:tailEnd"), {"type": head, "w": "med", "len": "med"})
        ln.append(e)
    return c


def table(s, x, y, w, col_w, rows, size=15, row_h=32, bold_last=False):
    shape = s.shapes.add_table(len(rows), len(col_w), Pt(x), Pt(y), Pt(w), Pt(row_h * len(rows)))
    tbl = shape.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Pt(cw)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Pt(row_h)
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = BLACK if i == 0 else (PANEL if i % 2 else BG)
            c.margin_left = c.margin_right = Pt(8)
            c.margin_top = c.margin_bottom = Pt(3)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            r = c.text_frame.paragraphs[0].add_run()
            r.text = val
            set_font(r, size, bold=i == 0 or (bold_last and i == len(rows) - 1), color=WHITE)
    return tbl


# 1 ─ Title ───────────────────────────────────────────────────────────────
s = new_slide(
    "สวัสดีครับ ผมนายเมทนี พูลสมบัติ รหัส 6821500060 วันนี้จะนำเสนองานวิชา Object-Oriented Programming "
    "คือระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ "
    "ก่อนเริ่ม ขอบอกว่าทุกข้ออ้างในสไลด์ชุดนี้ชี้ไปที่โค้ดจริงใน repo ใต้ตัวอย่างโค้ดจะมีชื่อไฟล์และบรรทัดกำกับไว้ "
    "อาจารย์เปิดตรวจตามได้ทันทีครับ"
)
rect(s, 0, 0, 14, H, fill=ACCENT)
text(s, 70, 110, 840, 30, "OBJECT-ORIENTED PROGRAMMING · COURSE PRESENTATION", size=15, bold=True, color=ACCENT)
text(s, 70, 145, 840, 130, ["ระบบผู้ช่วยจัดการคดี", "และตารางนัดหมายสำหรับทนายความ"], size=42, bold=True, spacing=0)
text(s, 70, 278, 840, 34, "Law Firm Case & Schedule Assistant · การออกแบบเชิง OOP", size=22, color=MUTED)
rect(s, 70, 330, 120, 3, fill=ACCENT)
text(s, 70, 352, 840, 90, [
    ("นายเมทนี พูลสมบัติ  ·  รหัสนักศึกษา 6821500060", {"size": 20}),
    ("FastAPI · Jinja2 · MariaDB · pytest", {"size": 16, "color": MUTED}),
], spacing=8)

# 2 ─ Problem & users ──────────────────────────────────────────────────────
s = new_slide(
    "ปัญหาตั้งต้นมาจากสำนักงานกฎหมายที่ยังใช้สมุดกับแชตจัดงาน มีสี่เรื่อง "
    "หนึ่ง รับนัดใหม่โดยไม่รู้ว่าวันนั้นมีนัดคดีอื่นอยู่แล้ว สอง กำหนดยื่นตามกฎหมาย เช่น คำให้การ อุทธรณ์ ฎีกา ไม่มีอะไรนับวันให้ "
    "สาม มอบหมายงานทางแชต ไม่รู้ว่าทนายเห็นหรือรับงานแล้วหรือยัง และสี่ แจกคดีใหม่โดยไม่เห็นว่าใครงานแน่นแค่ไหน "
    "ระบบจึงมีผู้ใช้สามบทบาท ทนายดูนัดวันนี้และตอบรับคดี ผู้จัดการมอบหมายคดีตามภาระงาน และแอดมินจัดการบัญชี โดยแอดมินไม่เห็นเนื้อหาคดีเลยครับ"
)
title(s, "จัดงานด้วยสมุดและแชต ทำให้นัดชนและกำหนดหลุด", "ปัญหาและผู้ใช้ 3 บทบาท", num=2)
text(s, 40, 120, 880, 150, [
    "• รับนัดใหม่โดยไม่รู้ว่าวันนั้นมีนัดอีกคดีอยู่แล้ว",
    "• กำหนดยื่นตามกฎหมาย (คำให้การ / อุทธรณ์ / ฎีกา) ไม่มีอะไรนับวันให้",
    "• มอบหมายทางแชต ไม่รู้ว่าทนายเห็น รับไหว หรือรับไปแล้ว",
    "• แจกคดีใหม่โดยไม่เห็นว่าทนายแต่ละคนงานแน่นแค่ไหน",
], size=18, spacing=8)
for i, (role, desc) in enumerate([
    ("ทนาย", "ดูนัดวันนี้ ตอบรับ/ปฏิเสธคดี ดูรายการใกล้ครบกำหนด"),
    ("ผู้จัดการ", "มอบหมายคดีตามภาระงาน เปิดคดีใหม่ อนุมัติคำขอถอนตัว"),
    ("แอดมิน", "จัดการบัญชีผู้ใช้ ไม่เห็นเนื้อหาคดี"),
]):
    panel(s, 40 + i * 300, 300, 280, 160, role, [desc], size=16)
caption(s, 40, 478, 880, "อ้างอิง: PRODUCT.md · docs/proposal.md §1")

# 3 ─ Overview & stack ─────────────────────────────────────────────────────
s = new_slide(
    "ภาพรวมระบบเป็นเว็บเดียวใช้ฐานข้อมูลเดียว ฝั่งเว็บใช้ FastAPI กับ Jinja2 template ตกแต่งด้วย Pico.css และ HTMX "
    "ฝั่งข้อมูลใช้ MariaDB ต่อผ่าน mysql-connector ตรงๆ ไม่ใช้ ORM รันด้วย Docker และทดสอบด้วย pytest 90 เทส "
    "ผู้ใช้ล็อกอินครั้งเดียว แล้วหน้า dashboard จะพาไปหน้าแรกตามบทบาทของตัวเอง ภาพทั้งสามคือหน้าจริงจากระบบ "
    "ทนายเห็นปฏิทินกับรายการใกล้ครบกำหนด ผู้จัดการเห็นคิวงานและภาระงานของทนายแต่ละคน แอดมินเห็นแค่จำนวนผู้ใช้ "
    "รหัสผ่านเก็บแบบ scrypt และแสดงวันที่เป็น พ.ศ. แต่เก็บเป็น ค.ศ. ต่อไปจะเข้าเรื่องการออกแบบครับ"
)
title(s, "เว็บแอปเดียวบน FastAPI + MariaDB แยกหน้าแรกตามบทบาท", "ภาพรวมระบบ · tech stack", num=3)
for i, (shot, who, crop) in enumerate([("lawyer_today.png", "ทนาย → /schedule/today", (0, 0, 0, 0.4)),
                                       ("manager_dashboard.png", "ผู้จัดการ → /manager/dashboard", (0, 0, 0, 0.25)),
                                       ("admin_dashboard.png", "แอดมิน → /admin/dashboard", (0, 0, 0, 0))]):
    image(s, shot, 40 + i * 300, 118, 280, 175, crop=crop)
    text(s, 40 + i * 300, 298, 280, 22, who, size=13, color=ACCENT, bold=True, align=PP_ALIGN.CENTER)
panel(s, 40, 335, 430, 125, "Web layer", [
    "FastAPI 0.115 · Jinja2 · Pico.css + HTMX",
    "scrypt + signed-cookie session",
], size=15, spacing=4)
panel(s, 490, 335, 430, 125, "Data + infra", [
    "MariaDB 10.4 · mysql-connector ไม่ใช้ ORM",
    "Docker + phpMyAdmin · pytest 90 เทส",
], size=15, spacing=4)
caption(s, 40, 478, 880, "อ้างอิง: requirements.txt · Dockerfile · docker-compose.yml · README.md")

# 4 ─ 3-layer architecture ─────────────────────────────────────────────────
s = new_slide(
    "โค้ดแบ่งเป็นสามชั้น ชั้น api ดูแลหน้าเว็บ ชั้น repository คุยกับฐานข้อมูล และชั้น domain เก็บกติกาธุรกิจทั้งหมด "
    "กฎสำคัญคือการพึ่งพาไปทางเดียว api เรียก repository และ domain ได้ repository เรียก domain ได้ แต่ domain ไม่ import ใครเลย "
    "กฎนี้ตรวจได้จริงด้วยคำสั่ง grep ใน domain ต้องไม่เจอ from api หรือ from repository ซึ่งตอนนี้ผลเป็นศูนย์บรรทัด "
    "ส่วนการเปิดปิดการเชื่อมต่อฐานข้อมูลอยู่จุดเดียวคือ get_db ใน api/deps.py ที่ส่งเข้า route ผ่าน Depends ครับ"
)
title(s, "dependency ไปทางเดียว: domain ไม่ import ชั้นอื่น", "สถาปัตยกรรม 3 ชั้น", num=4)
for i, (name, a, b, fill, ln) in enumerate([
    ("api/ (web)", "routes/ · deps.py · auth.py", "39 routes · Depends(get_db)", PANEL, LINE),
    ("repository/ (persistence)", "Repository class ต่อตาราง + db.py", "map แถว ↔ object", PANEL, LINE),
    ("domain/ (business objects)", "กฎ BR-* ทั้งหมดอยู่ที่นี่", "import ได้แค่ stdlib + กันเอง", HILITE, ACCENT),
]):
    x = 40 + i * 300
    box(s, x, 125, 280, 125, [name, a, (b, {"color": MUTED})], fill=fill, line=ln, size=15)
line(s, 320, 187, 340, 187, head="triangle", width=2)
line(s, 620, 187, 640, 187, head="triangle", width=2)
for i, (t, c) in enumerate([("api → repository, domain", ACCENT), ("repository → domain", ACCENT),
                            ("domain → ไม่มีใคร (กฎ)", RED)]):
    text(s, 40 + i * 300, 260, 280, 26, t, size=15, color=c, align=PP_ALIGN.CENTER, bold=True)
text(s, 40, 310, 880, 80, [
    "• ตรวจกฎได้: grep -r \"from api\\|from repository\" domain/ ต้องว่างเปล่า (ตอนนี้ 0 บรรทัด)",
    "• DB เปิด/ปิดที่จุดเดียว: get_db ใน api/deps.py ผ่าน Depends",
], size=17, spacing=8)
caption(s, 40, 478, 880, "อ้างอิง: api/main.py (23 บรรทัด, factory) · api/deps.py · repository/db.py")

# 5 ─ Folder layout ────────────────────────────────────────────────────────
s = new_slide(
    "โครงโฟลเดอร์ตั้งใจให้แต่ละโฟลเดอร์มีหน้าที่เดียว domain คือกติกาธุรกิจ repository คือ SQL "
    "api คือ route ของหน้าเว็บ templates คือหน้าตา db เก็บ schema กับ seed และ tests เก็บเทสทั้งหมด "
    "api/main.py เดิมยาว 1,212 บรรทัด หลัง refactor เหลือ 23 บรรทัด เพราะแยก route ออกเป็น 7 โมดูล "
    "ถ้าถามว่าแยกทำไม คำตอบคือให้คนอ่านเดาได้ว่าโค้ดอยู่ไหนโดยไม่ต้องเปิดหาครับ"
)
title(s, "แต่ละโฟลเดอร์มีหน้าที่เดียว", "โครงโฟลเดอร์", num=5)
table(s, 40, 125, 880, [180, 700], [
    ["โฟลเดอร์", "หน้าที่"],
    ["domain/", "กติกาธุรกิจ: Person, Case, Appointment, Schedule, CaseAssignment, …"],
    ["repository/", "Repository class ต่อตาราง คุย MariaDB ตรงๆ ไม่ใช้ ORM"],
    ["api/", "main.py factory บางๆ · deps.py ของใช้ร่วม · routes/ · auth.py"],
    ["templates/ · static/", "Jinja2 (Pico.css + HTMX) · theme.css"],
    ["db/", "schema.sql · seed.sql · migrations/"],
    ["tools/ · tests/", "generate_seed.py สร้าง seed · pytest 90 เทส"],
    ["docs/", "proposal · backlog · uml · slides"],
], size=15, row_h=36)
rect(s, 40, 430, 880, 38, fill=HILITE)
text(s, 50, 434, 860, 30, "api/main.py 1,212 → 23 บรรทัด  ·  routes/ 7 โมดูล 39 routes", size=17, bold=True,
     anchor=MSO_ANCHOR.MIDDLE)
caption(s, 40, 478, 880, "อ้างอิง: README.md §โครงสร้างโปรเจกต์")

# 6 ─ Class diagram: people ────────────────────────────────────────────────
s = new_slide(
    "class diagram ฝั่งคน ลูกศรหัวสามเหลี่ยมทุกเส้นคือการสืบทอด ชี้ขึ้นหาคลาสแม่ "
    "Person เป็นคลาส abstract บนสุด มีชื่อ เลขบัตร และเบอร์โทร SystemUser สืบจาก Person และเพิ่ม username password และสถานะใช้งาน "
    "Lawyer Manager และ Admin สืบจาก SystemUser ส่วน Client ลูกความ สืบจาก Person ตรงๆ ไม่ผ่าน SystemUser "
    "เพราะลูกความไม่ได้ล็อกอินเข้าระบบ ไดอะแกรมนี้ตรงกับ domain/person.py ครับ"
)
title(s, "Person → SystemUser → ผู้ใช้ 3 บทบาท · Client สืบจาก Person", "CLASS DIAGRAM ฝั่งคน (1/2) · ลูกศรหัวสามเหลี่ยม = สืบทอด", num=6)
box(s, 300, 120, 300, 80, ["Person «abstract»", ("name · citizen_id · phone", {"color": MUTED}),
                           "display_name()* · contact_info()"])
box(s, 300, 235, 300, 92, ["SystemUser «abstract»", ("username · password_hash · is_active", {"color": MUTED}),
                           "can_view_case()* · dashboard_cards()*", "home_url()*"])
line(s, 450, 235, 450, 200, head="triangle")
kids = [("Lawyer", "+license_no", 60), ("Manager", "", 260), ("Admin", "", 460)]
for name, attr, x in kids:
    box(s, x, 395, 180, 52, [name] + ([attr] if attr else []), fill=HILITE, line=ACCENT)
    line(s, x + 90, 395, x + 90, 365)
line(s, 150, 365, 550, 365)
line(s, 450, 365, 450, 327, head="triangle")
box(s, 720, 395, 200, 52, ["Client", "+company"])
line(s, 820, 395, 820, 160)
line(s, 820, 160, 600, 160, head="triangle")
text(s, 640, 250, 280, 60, ["Client ไม่ได้ล็อกอิน", ("สืบจาก Person ตรง", {"color": MUTED})], size=14)
text(s, 40, 125, 240, 80, [("* = abstract method", {"color": MUTED}), ("ลูกต้อง override", {"color": MUTED})],
     size=13)
caption(s, 40, 478, 880, "อ้างอิง: domain/person.py · docs/uml.md §1")

# 7 ─ Class diagram: case & schedule (simplified; full version is backup B7) ──
s = new_slide(
    "ฝั่งคดีและตาราง ตรงกลางคือ Case เก็บสถานะและรายการมอบหมายไว้เป็น private คดีหนึ่งมี CaseAssignment ได้หลายรายการ "
    "ซ้ายล่าง Appointment เป็นคลาส abstract มีลูกสามชนิด ขวามือ Schedule ไม่ได้สร้างนัดเอง "
    "แค่ยืมรายการนัดจาก repository มาตรวจนัดชน ฉบับเต็มของแผนภาพนี้อยู่ในสไลด์สำรอง B7 ครับ"
)
title(s, "Case เป็นศูนย์กลาง ถือการมอบหมาย นัด และโน้ต", "CLASS DIAGRAM ฝั่งคดีและตาราง (2/2) · หัวสามเหลี่ยม = สืบทอด · เส้นธรรมดา = ความสัมพันธ์", num=7)
box(s, 40, 118, 270, 84, ["CaseAssignment (−status)", "accept() · decline()"], size=12)
box(s, 340, 118, 280, 84, ["Case (−status, −assignments)", "assign_lawyer() · advance_status()"],
    fill=HILITE, line=ACCENT, size=12)
box(s, 650, 118, 270, 84, ["Schedule", "add() · find_conflicts()"], size=12)
line(s, 310, 160, 340, 160)
text(s, 306, 160, 20, 20, "*", size=14, color=ACCENT)
text(s, 326, 160, 20, 20, "1", size=13, color=ACCENT)
text(s, 40, 204, 270, 22, "หลายรายการ ต่อ 1 Lawyer (สไลด์ 4)", size=12, color=ACCENT, align=PP_ALIGN.CENTER)
line(s, 785, 202, 785, 250, dash=True)
text(s, 790, 210, 130, 22, "◇ ยืมลิสต์นัด", size=12, color=ACCENT)
box(s, 40, 240, 270, 100, ["Appointment «abstract»", "reminder_lead_days()* · kind_label()*"], size=12)
box(s, 40, 372, 270, 80, ["CourtHearing · ClientMeeting", "FilingDeadline",
                          ("นัดศาล 3 วัน · พบลูกความ 1 วัน · ยื่น 15 วัน", {"color": MUTED})],
    fill=HILITE, line=ACCENT, size=12)
line(s, 175, 372, 175, 340, head="triangle")
line(s, 480, 202, 480, 240)
text(s, 484, 204, 30, 20, "1", size=13, color=ACCENT)
text(s, 484, 222, 30, 20, "*", size=14, color=ACCENT)
box(s, 340, 240, 280, 70, ["CaseNote · CaseEvent", "คดี 1 : * (ผูกด้วย case_id)"], size=12)
box(s, 340, 325, 280, 55, ["Client", ("ลูกความ 1 : คดี * (case.client)", {"color": MUTED})], size=12)
box(s, 650, 250, 270, 100, ["«enum» · @dataclass", "CaseStatus 7 ค่า", "AssignmentStatus 4 ค่า"], size=12)
text(s, 340, 395, 580, 50, ["Case 1 : * มอบหมาย / นัด / โน้ต",
                            "Schedule ◇ นัด * (ยืมลิสต์นัดจาก repo มาตรวจ)"], size=13, color=ACCENT)
caption(s, 40, 478, 880, "อ้างอิง: domain/case.py · assignment.py · appointment.py · schedule.py")

# 8 ─ Abstraction ──────────────────────────────────────────────────────────
s = new_slide(
    "เริ่มหลัก OOP ข้อแรก Abstraction คลาสแม่ประกาศสัญญาด้วย ABC กับ abstractmethod ว่าลูกต้องมีเมธอดอะไรบ้าง "
    "ซ้ายคือ Person กับ SystemUser ที่บังคับให้ลูกมี display_name, can_view_case, dashboard_cards และ home_url "
    "ขวาคือ Appointment ที่บังคับ reminder_lead_days, can_reschedule และ kind_label "
    "ผลคือสร้าง Appointment ตรงๆ ไม่ได้ Python จะโยน TypeError ทันที ผู้เรียกจึงพึ่งแค่สัญญา ไม่ต้องรู้ว่าเป็นลูกตัวไหน "
    "ส่วนเมธอดที่ใช้ร่วมกันจริง เช่น contact_info กับ overlaps เขียนไว้ที่แม่ครั้งเดียว ไม่ต้องเขียนซ้ำในลูกครับ"
)
title(s, "คลาสแม่เป็น ABC: สร้างตรงไม่ได้ ลูกต้องเขียนเมธอดที่กำหนด", "ABSTRACTION · คลาสแม่กำหนดเมธอดที่ลูกต้องมี", num=8)
defn(s, "คลาสแม่บอกว่าลูกต้องมีเมธอดอะไร แต่ไม่บอกว่าทำยังไง")
code(s, 40, 142, 430, 185, [
    "# domain/person.py:15,30",
    "class Person(ABC):",
    "    @abstractmethod",
    "!    def display_name(self): ...",
    "",
    "class SystemUser(Person):",
    "    @abstractmethod can_view_case()",
    "    @abstractmethod dashboard_cards()",
    "    @abstractmethod home_url()",
], size=14)
code(s, 490, 142, 430, 185, [
    "# domain/appointment.py:29",
    "class Appointment(ABC):",
    "    @abstractmethod",
    "!    def reminder_lead_days(self): ...",
    "    @abstractmethod",
    "    def can_reschedule(self): ...",
    "    @abstractmethod",
    "    def kind_label(self): ...",
], size=14)
code(s, 490, 345, 430, 62, [
    "Appointment(...)  →  TypeError:",
    "Can't instantiate abstract class ...",
], size=14)
text(s, 40, 335, 430, 70, [
    "• contact_info()/overlaps() เขียนที่แม่ครั้งเดียว ลูกทุกตัวใช้ร่วมกัน",
], size=16, spacing=8)
result_bar(s, 412, "ผลที่ได้: สร้าง Appointment() ตรงๆ ไม่ได้ ต้องสร้างคลาสลูก", h=40, size=16)
caption(s, 40, 478, 880, "อ้างอิง: domain/person.py · domain/appointment.py")

# 9 ─ Inheritance ──────────────────────────────────────────────────────────
s = new_slide(
    "Inheritance คลาสลูกได้ทุกอย่างจากแม่ แล้วเติมของตัวเอง "
    "Lawyer, Manager และ Admin ได้ username และ password จาก SystemUser แล้วแต่ละตัวเขียน display_name ของตัวเอง "
    "Lawyer ได้ทั้ง name phone จาก Person และ username password จาก SystemUser โดยไม่ต้องเขียนซ้ำ "
    "Lawyer เพิ่มแค่เลขใบอนุญาตว่าความ ส่วน Client สืบจาก Person ตรงๆ "
    "จุดที่อาจารย์มักถามคือ ทำไม Client ไม่สืบจาก SystemUser คำตอบคือลูกความไม่มี username และ password "
    "จึงไม่ผ่านความสัมพันธ์แบบ is-a กับผู้ใช้ระบบครับ"
)
title(s, "ลูกแต่ละคลาสเติม attribute และ display_name() ของตัวเอง", "INHERITANCE · ลูกได้ของจากแม่แล้วเติมของตัวเอง", num=9)
defn(s, "ลูกได้ทุกอย่างจากแม่ แล้วเติมของตัวเอง")
t_inherit = table(s, 40, 148, 880, [250, 630], [
    ["คลาส", "ได้จากแม่ / เติมเอง"],
    ["Person(ABC)", "@abstractmethod display_name()"],
    ["SystemUser(Person)", "username · password_hash · is_active"],
    ["Lawyer(SystemUser)", "+ license_no · display_name() → \"ทนาย…\""],
    ["Manager(SystemUser)", "display_name() → \"ผู้จัดการ…\""],
    ["Admin(SystemUser)", "display_name() → \"ผู้ดูแลระบบ…\""],
    ["Client(Person)", "+ company (ลูกความไม่ได้ล็อกอิน จึงสืบจาก Person ตรง)"],
], size=16, row_h=32)
for _p in t_inherit.cell(3, 1).text_frame.paragraphs:
    for _r in _p.runs:
        _r.font.color.rgb = ACCENT
        _r.font.bold = True
result_bar(s, 412, "ผลที่ได้: Lawyer มี name/phone โดยไม่ต้องเขียนซ้ำ · Client ไม่ใช่ SystemUser", h=52, size=16)
caption(s, 40, 478, 880, "อ้างอิง: domain/person.py:15,30,50,75,90,105")

# 10 ─ Polymorphism (home_url only) ───────────────────────────────────────────
s = new_slide(
    "Polymorphism คือเรียกเมธอดชื่อเดียว แต่ละคลาสตอบไม่เหมือนกัน ตัวอย่างคือ home_url "
    "ทนายไปหน้าตารางวันนี้ ผู้จัดการไปหน้า dashboard ของผู้จัดการ แอดมินไปหน้าแอดมิน "
    "route เรียกแค่ current_user.home_url() บรรทัดเดียว ไม่ต้องถามว่าเป็น role ไหน หน้าแรกสามแบบในสไลด์ 3 มาจากบรรทัดนี้ครับ "
    "ส่วน reminder_lead_days ของนัดสามชนิดก็เรียกบรรทัดเดียวเหมือนกันครับ"
)
title(s, "เรียก home_url() ชื่อเดียว ได้หน้าแรกตามบทบาท", "POLYMORPHISM · เรียกเมธอดเดียว ได้พฤติกรรมตามชนิด", num=10)
defn(s, "เรียกเมธอดชื่อเดียว แต่ละคลาสตอบไม่เหมือนกัน")
code(s, 40, 142, 540, 240, [
    "# domain/person.py:63,85,100",
    "class Lawyer(SystemUser):",
    "    def home_url(self) -> str:",
    "!        return \"/schedule/today\"",
    "class Manager(SystemUser):",
    "    def home_url(self) -> str:",
    "!        return \"/manager/dashboard\"",
    "class Admin(SystemUser):",
    "    def home_url(self) -> str:",
    "!        return \"/admin/dashboard\"",
], size=14)
code(s, 600, 142, 320, 110, [
    "# api/routes/dashboard.py",
    "return RedirectResponse(",
    "    current_user.home_url())",
], size=16)
result_bar(s, 396, "ผลที่ได้: home_url() บรรทัดเดียว ได้หน้าแรก 3 แบบ (ดูภาพหน้า 3)", h=44, size=16)
caption(s, 40, 478, 880, "อ้างอิง: domain/person.py · api/routes/dashboard.py (ตัดบางบรรทัด)")

# 11 ─ Encapsulation ───────────────────────────────────────────────────────
s = new_slide(
    "Encapsulation สถานะของคดีกับสถานะการมอบหมายแก้ตรงจากข้างนอกไม่ได้ "
    "เก็บไว้ใน _status และเปิดให้อ่านผ่าน property status ที่ไม่มี setter ถ้าสั่ง case.status = ... จะได้ AttributeError "
    "การเปลี่ยนสถานะต้องผ่านเมธอดที่ตรวจกฎก่อน เช่น advance_status ต้องเลื่อนทีละขั้น "
    "และจะยื่นฟ้องได้ต้องมีทนายตอบรับแล้ว ถ้าผิดกฎจะโยน error "
    "ภาพขวาคือหน้าคดีจริง คดีนี้อยู่ขั้นสืบพยาน ปุ่มจึงเสนอแค่ขั้นถัดไปคือตัดสิน เพราะ advance_status ไม่ยอมให้ข้ามขั้น "
    "ข้อยกเว้นมีที่เดียวคือ repository ตั้ง _status ตรงตอนโหลดแถวเดิมจากฐาน ค่านั้นผ่านกฎมาแล้วตอนบันทึก จึงไม่ต้องตรวจซ้ำครับ"
)
title(s, "เปลี่ยนสถานะได้ผ่านเมธอดที่ตรวจกฎเท่านั้น", "ENCAPSULATION · แก้สถานะตรงจากข้างนอกไม่ได้", num=11)
defn(s, "ข้อมูลสำคัญแก้ได้ผ่านเมธอดที่ตรวจกฎเท่านั้น")
code(s, 40, 142, 440, 165, [
    "# domain/case.py",
    "_status: CaseStatus = field(...OPEN...)",
    "@property",
    "def status(self): ...",
    "    # ไม่มี setter: แก้ตรงได้ AttributeError",
    "def advance_status(self, ...):",
    "    # ตรวจกฎก่อนเปลี่ยนสถานะ",
    "!    self._status = new_status",
], size=12)
code(s, 40, 317, 440, 100, [
    "# domain/assignment.py",
    "def accept(self):",
    "    # ตรวจว่ายังรอตอบรับอยู่",
    "!    self._status = AssignmentStatus.ACCEPTED",
], size=12)
text(s, 500, 370, 420, 42, "ข้อยกเว้น: repository ตั้ง _status ตอนโหลดแถวเดิมจาก DB (ผ่านกฎมาแล้วตอนบันทึก)",
     size=13, color=MUTED)
image(s, "case_detail.png", 500, 142, 420, 220, crop=(0, 0, 0, 0.4))
result_bar(s, 420, "ผลที่ได้: ข้ามขั้นไม่ได้ ปุ่มเสนอแค่ขั้นถัดไป \"ตัดสิน\"", h=40, size=16)
caption(s, 40, 478, 880, "อ้างอิง: domain/case.py · domain/assignment.py")

# 12 ─ Repository pattern ──────────────────────────────────────────────────
s = new_slide(
    "Repository pattern SQL ทั้งหมดอยู่ใน repository ที่เดียว domain ไม่เคยเห็น SQL และ repository ไม่รู้จักกฎธุรกิจ "
    "แต่ละตารางมีคลาสของตัวเอง เช่น CaseRepository ถือ connection ไว้หนึ่งตัว และคืนค่าเป็น object ของ domain "
    "ตัวอย่างที่สอง UserRepository อ่านคอลัมน์ role แล้วสร้าง object ให้ตรงคลาสลูก Lawyer Manager หรือ Admin "
    "ถ้าถามว่าทำไมไม่ใช้ ORM ตอบว่าโปรเจกต์ขนาดนี้ SQL ตรงๆ อ่านง่ายกว่า และถ้าวันหนึ่งย้ายฐานข้อมูล ก็แก้แค่ repository ครับ"
)
title(s, "SQL ทั้งหมดอยู่ใน repository/ · กฎทั้งหมดอยู่ใน domain/", "REPOSITORY PATTERN · Repository class ต่อตาราง", num=12)
code(s, 40, 120, 880, 62, [
    "cases = CaseRepository(conn)        # ถือ connection ไว้หนึ่งตัว",
    "case = cases.get_by_id(case_id)     # คืน object ไม่ใช่ dict/row",
], size=14)
code(s, 40, 194, 880, 62, [
    "_ROLE_TO_CLASS = {\"lawyer\": Lawyer, \"manager\": Manager, \"admin\": Admin}",
    "cls = _ROLE_TO_CLASS[row[\"role\"]]   # อ่าน role แล้วสร้างให้ตรงคลาสลูก",
], size=14)
code(s, 40, 268, 880, 100, [
    "# repository/case_repo.py: peer repo ใช้ connection เดียวกัน",
    "def __init__(self, conn, clients=None, users=None):",
    "    self._conn = conn",
    "    self._clients = clients or ClientRepository(conn)",
], size=14)
text(s, 40, 385, 880, 70, [
    "• ทำไมไม่ใช้ ORM: โปรเจกต์เล็ก SQL ตรงๆ อ่านง่ายกว่า",
    "• ย้ายฐานข้อมูล: แก้ที่ repository/ ที่เดียว",
], size=16, spacing=6)
caption(s, 40, 478, 880, "อ้างอิง: repository/case_repo.py · repository/user_repo.py")

# 13 ─ Exception hierarchy ─────────────────────────────────────────────────
s = new_slide(
    "Exception hierarchy error ทุกตัวในระบบเป็นคลาส มีแม่คือ DomainError และลูกสี่ตัวตามกลุ่มกฎ "
    "นัดชนตาม BR-1 เปลี่ยนสถานะผิดตาม BR-7 8 9 18 เลื่อนนัดไม่ได้ตาม BR-3 กับ 5 และการมอบหมายผิดกฎ BR-15 ถึง 19 "
    "ชั้น api ไม่มี handler กลาง แต่ละ route จับ subclass ของตัวเองแล้วแปลเป็นภาษาคน "
    "เช่น นัดชนก็แสดงฟอร์มเดิมพร้อมข้อความ หรือมอบหมายผิดก็ตอบ HTTP 409 เทสต้อง assert ชนิด subclass ที่เจาะจงครับ"
)
title(s, "DomainError กับลูก 4 ชนิด · api แปลเป็นข้อความไทย", "EXCEPTION HIERARCHY · แยก error ตามกลุ่มกฎ", num=13)
code(s, 40, 125, 430, 190, [
    "DomainError (แม่)",
    "├ ScheduleConflictError  นัดเวลาชนกัน",
    "├ InvalidStatusTransition  ข้ามขั้นสถานะ",
    "├ RescheduleNotAllowed  เลื่อนนัดไม่ได้",
    "└ AssignmentError  มอบหมาย/รับคดีผิดกฎ",
], size=14)
code(s, 490, 125, 430, 96, [
    "try: schedule.add(appt)",
    "except ScheduleConflictError as e:",
    "    → ฟอร์มเดิม + \"นัดชน…\"",
], size=15)
code(s, 490, 225, 430, 96, [
    "except AssignmentError as e:",
    "    → HTTP 409 \"รับได้เฉพาะ…\"",
], size=15)
result_bar(s, 418, "ทำผิดกฎ → โยน error ชนิดเฉพาะ → หน้าเว็บแสดงข้อความไทย", h=44, size=16)
caption(s, 40, 478, 880, "อ้างอิง: domain/errors.py")

# 14 ─ Case flow ───────────────────────────────────────────────────────────
s = new_slide(
    "flow ของคดีตั้งแต่เปิดจนปิด ขั้นหลักทั้งห้าขั้นมีเมธอดใน domain คุมกฎ "
    "ผู้จัดการเปิดคดี มอบหมายทนายด้วย assign_lawyer ทนายตอบรับหรือปฏิเสธด้วย accept หรือ decline "
    "จากนั้นเพิ่มนัดและเลื่อนสถานะคดี จนปิดคดีได้เมื่อ can_close เป็นจริง คือไม่มีนัดหรือกำหนดยื่นค้าง "
    "ทางแยกสีแดงคือการถอนตัว ทนายขอถอนตัว ผู้จัดการอนุมัติหรือไม่อนุมัติ ถ้าอนุมัติก็ย้ายหรือยกเลิกนัด "
    "ขั้นย้ายและยกเลิกนัดเป็นงานของ AppointmentRepository โดยตรง ไม่มีกฎใน domain คุม "
    "ถ้าถามชื่อเมธอด ขั้นหลักคือ Case กับ repo.add assign_lawyer accept decline add advance_status can_close "
    "ส่วนทางแยกคือ request_withdraw approve reject_withdraw reassign cancel ครับ"
)
title(s, "เส้นทางคดีจากเปิดถึงปิด และทางแยกเมื่อทนายขอถอนตัว", "FLOW ของคดี", num=14)
steps = ["เปิดคดี", "มอบหมายทนาย", "รับ / ปฏิเสธ", "นัด + เลื่อนสถานะ", "ปิดคดี"]
for i, a in enumerate(steps):
    x = 40 + i * 180
    box(s, x, 130, 160, 74, [a], size=14)
    if i:
        line(s, x - 20, 167, x, 167, head="triangle", width=2)
red = [("ขอถอนตัว", 220), ("อนุมัติ / ไม่อนุมัติ", 400), ("ย้าย / ยกเลิกนัด", 580)]
for a, x in red:
    box(s, x, 265, 160, 80, [a], fill=RED_BG, line=RED, size=14)
line(s, 480, 204, 480, 265, color=RED, head="triangle", dash=True, width=2)
line(s, 380, 305, 400, 305, color=RED, head="triangle", width=2)
line(s, 560, 305, 580, 305, color=RED, head="triangle", width=2)
text(s, 760, 280, 160, 50, ["กล่องแดง =", "ทางแยกถอนตัว"], size=14, color=MUTED)
text(s, 40, 395, 880, 60, [
    "• เส้นทึบ = ทางหลัก · เส้นประแดง = ทางแยกถอนตัว",
    "• ปิดคดีได้เมื่อไม่มีนัดในอนาคตหรือกำหนดยื่นค้าง",
], size=15, spacing=4)
caption(s, 40, 478, 880, "อ้างอิง: api/routes/manager.py · domain/case.py · assignment.py · schedule.py · repository/appointment_repo.py")

# 15 ─ Flow on screen ──────────────────────────────────────────────────────
s = new_slide(
    "สไลด์นี้คือ flow เดียวกันบนหน้าจอจริง ซ้ายคือหน้ามอบหมายของผู้จัดการ เรียงทนายจากภาระงานน้อยไปมาก "
    "คนที่งานเกินจะมีป้ายเตือน ผู้จัดการจึงเลือกคนที่ว่างกว่าได้ทันที "
    "กลางคือ popup คดีรอตอบรับของทนาย มีปุ่มรับคดีกับปฏิเสธ ซึ่งเรียก accept และ decline "
    "ขวาคือหน้าคดีหลังทนายรับแล้ว มีตารางนัด ปุ่มเลื่อนสถานะ และปุ่มขอถอนตัวจากคดี ซึ่งเป็นจุดเริ่มของทางแยกสีแดงในสไลด์ flow คดีครับ"
)
title(s, "flow เดียวกันบนหน้าจอจริง", "มอบหมาย → รับ / ปฏิเสธ → จัดการคดี", num=15)
for i, (shot, step, desc, crop) in enumerate([
    ("manager_assign.png", "1. มอบหมายทนาย", "ผู้จัดการเห็นภาระงานทุกคนก่อนเลือก", (0, 0, 0, 0.2)),
    ("pending_dialog.png", "2. รับ / ปฏิเสธ", "popup คดีรอตอบรับ: accept() · decline()", (0, 0, 0, 0)),
    ("case_detail.png", "3. นัด · เลื่อนสถานะ · ขอถอนตัว", "หน้าคดีหลังทนายรับงาน", (0, 0, 0, 0.35)),
]):
    x = 40 + i * 300
    text(s, x, 118, 280, 26, step, size=16, bold=True, color=ACCENT)
    image(s, shot, x, 150, 280, 250, crop=crop)
    text(s, x, 408, 280, 44, desc, size=14, color=MUTED, align=PP_ALIGN.CENTER)
caption(s, 40, 478, 880, "ภาพจาก http://localhost:8000 (ข้อมูล seed) · manager1 และ lawyer1")

# 16 ─ Testing ─────────────────────────────────────────────────────────────
s = new_slide(
    "การทดสอบมี 90 เทส แบ่งตามไฟล์ตามตาราง ส่วนใหญ่ทดสอบชั้น domain ซึ่งไม่ต้องใช้ฐานข้อมูลเลย "
    "เทส repository 12 เทสวิ่งบนฐานข้อมูลแยกชื่อ lawfirm_test "
    "ตอนแรก fixture ของเทสสั่ง TRUNCATE ฐาน lawfirm-db ของแอปตัวจริง ทำให้ข้อมูลหายไปครั้งหนึ่ง "
    "ตอนนี้แก้แล้ว เทสสร้างฐาน lawfirm_test ลง schema ให้เอง และมี guard ที่สั่ง pytest.fail ก่อน TRUNCATE ถ้าชื่อฐานชนกับของจริง "
    "และมีเทส guard อีก 4 เคสที่ไม่ต้องใช้ฐานข้อมูล คอยกันไม่ให้เกิดซ้ำครับ"
)
title(s, "90 เทส: domain เทสโดยไม่ใช้ DB · เทส DB ใช้ฐานแยก", "TESTING · เคยล้างฐานจริงมาแล้วหนึ่งครั้ง", num=16)
table(s, 40, 120, 480, [160, 80, 160, 80], [
    ["ไฟล์", "จำนวน", "ไฟล์", "จำนวน"],
    ["appointment", "10", "assignment", "19"],
    ["case", "19", "person", "8"],
    ["schedule", "12", "auth", "6"],
    ["repository", "12", "db_safety", "4"],
    ["รวม", "", "", "90"],
], size=16, row_h=40, bold_last=True)
panel(s, 540, 120, 380, 240, "บทเรียนจริง", [
    "fixture เคย TRUNCATE ฐาน lawfirm-db ของแอป",
    "ตอนนี้เทสใช้ lawfirm_test สร้าง + ลง schema เอง",
    "guard pytest.fail ก่อน TRUNCATE ถ้าชื่อชน",
], size=15, spacing=8)
text(s, 40, 380, 880, 60, [
    "• repository 12 เทสวิ่งบนฐานแยก · db_safety 4 เทสตรวจ guard โดยไม่ต้องใช้ DB",
], size=15)
caption(s, 40, 478, 880, "อ้างอิง: pytest --collect-only · tests/test_repository.py · tests/test_db_safety.py · repository/db.py")

# 17 ─ Demo script ─────────────────────────────────────────────────────────
s = new_slide(
    "ต่อไปเป็น demo มีสามฉาก ทุกบัญชีใช้รหัสผ่าน password123 "
    "ฉากแรก lawyer1 เปิด popup คดีรอตอบรับ กดรับคดี แล้วเพิ่มนัดศาลพรุ่งนี้ จากนั้นดูแผงรายการใกล้ครบกำหนด "
    "ฉากสอง manager1 ดูคิวคดีที่ยังไม่มีทนายตอบรับ กดมอบหมาย แล้วเปิดคำขอถอนตัว กดอนุมัติพร้อมย้ายนัด "
    "ฉากสาม admin เพิ่มผู้ใช้ใหม่เป็นทนาย ปิดใช้งาน แล้วเปิดคืน "
    "ถ้าเวลาน้อย จะเล่นแค่ฉากทนาย คือรับคดีกับเพิ่มนัด ก็เห็น loop หลักของระบบครบครับ"
)
title(s, "Demo 3 ฉาก: ทนาย ผู้จัดการ แอดมิน", "DEMO SCRIPT · http://localhost:8000 · ทุกบัญชีใช้รหัส password123", num=17)
for i, (who, steps) in enumerate([
    ("lawyer1", ["1. เปิด popup \"คดีรอตอบรับ\"", "2. กดรับคดี", "3. \"+ เพิ่มนัด\" นัดศาลพรุ่งนี้",
                 "4. ดูแผงใกล้ครบกำหนด"]),
    ("manager1", ["1. ดูคิว \"ยังไม่มีทนายตอบรับ\"", "2. กดมอบหมาย", "3. เปิดคำขอถอนตัว",
                  "4. อนุมัติพร้อมย้ายนัด"]),
    ("admin", ["1. \"+ เพิ่มผู้ใช้ใหม่\"", "2. สร้างทนาย", "3. ปิดใช้งาน", "4. เปิดคืน"]),
]):
    x = 40 + i * 300
    image(s, ["pending_dialog.png", "manager_dashboard.png", "admin_users.png"][i], x, 118, 280, 165,
          crop=[(0, 0, 0, 0), (0, 0, 0, 0.25), (0, 0, 0, 0.45)][i])
    panel(s, x, 292, 280, 160, who, steps, size=14, spacing=2)
text(s, 40, 456, 880, 22, "เวลาน้อย: เล่นแค่ฉาก lawyer1 (รับคดี + เพิ่มนัด) ก็เห็น loop หลักครบ", size=14,
     color=ACCENT, bold=True)
caption(s, 40, 478, 880, "อ้างอิง: README.md §บัญชีตัวอย่าง · seed มี lawyer1 ถึง lawyer8 · manager1 · admin")

# 18 ─ Summary ─────────────────────────────────────────────────────────────
s = new_slide(
    "สรุป สี่หลักของ OOP ที่โชว์ในระบบนี้ "
    "Encapsulation สถานะคดีและการมอบหมายอ่านได้อย่างเดียว เปลี่ยนผ่านเมธอดที่ตรวจกฎ "
    "Abstraction Person SystemUser และ Appointment ประกาศสัญญาให้ลูกเติม "
    "Inheritance ผู้ใช้สามบทบาทสืบจาก SystemUser และนัดสามชนิดสืบจาก Appointment ซึ่งเป็น is-a จริง "
    "Polymorphism home_url กับ reminder_lead_days เรียกบรรทัดเดียวไม่ต้องถามชนิด "
    "นอกจากนี้ยังแยกชั้นสถาปัตยกรรมให้พึ่งพาไปทางเดียว ซึ่งตรวจได้ด้วย grep "
    "งานต่อยอดคือแจ้งเตือนทางอีเมลหรือไลน์ ซิงก์ปฏิทิน และสิทธิ์ละเอียดต่อคดี "
    "กฎทั้งหมดนี้มีเทสคุม 90 เทส ผ่านทั้งหมด "
    "กฎธุรกิจทั้งหมดอยู่ในเมธอดของคลาสใน domain ขอบคุณครับ เปิดรับคำถามครับ"
)
title(s, "สรุป 4 หลัก OOP และงานต่อยอด", num=18)
table(s, 40, 120, 880, [190, 690], [
    ["หลัก", "ในระบบนี้"],
    ["Encapsulation", "Case._status / CaseAssignment._status อ่านอย่างเดียว เปลี่ยนผ่านเมธอด"],
    ["Abstraction", "Person / SystemUser / Appointment ประกาศสัญญา ลูกต้องเติม"],
    ["Inheritance", "Lawyer/Manager/Admin สืบ SystemUser · นัด 3 ชนิดสืบ Appointment"],
    ["Polymorphism", "home_url() / reminder_lead_days() เรียกบรรทัดเดียว ไม่ถามชนิด"],
    ["Separation", "api → repository → domain ทิศทางเดียว ตรวจด้วย grep ได้"],
], size=15, row_h=36)
text(s, 40, 344, 880, 30, "เทส: 90 เทสผ่านทั้งหมด · domain เทสโดยไม่ใช้ DB · repository เทสบนฐานแยก", size=15)
text(s, 40, 378, 880, 30, "ต่อยอด: แจ้งเตือนทางอีเมล/ไลน์ · ซิงก์ปฏิทิน · สิทธิ์ละเอียดต่อคดี (ตอนนี้ manager เห็นหมด)",
     size=15, color=MUTED)
rect(s, 40, 418, 880, 44, fill=HILITE)
text(s, 50, 422, 860, 36, "กฎธุรกิจทั้งหมดอยู่ในเมธอดของคลาสใน domain/", size=19, bold=True,
     anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)

# 19 ─ Backup: expected questions ──────────────────────────────────────────
s = new_slide(
    "สไลด์สำรองสำหรับตอบคำถาม เปิดเฉพาะเมื่อถูกถาม "
    "ถ้าถามว่า _status ยังเขียนทับได้ไหม ตอบตรงๆ ว่าได้ เพราะ Python ไม่มี private จริง ขีดล่างหนึ่งตัวเป็นข้อตกลงว่าห้ามแตะ "
    "สิ่งที่กันจริงคือ property ที่ไม่มี setter ถ้าต้องการกันมากขึ้นใช้ขีดล่างสองตัวให้เกิด name mangling ได้ "
    "ถ้าถามว่าทำไมไม่มี interface ตอบว่า Python ไม่มีคีย์เวิร์ด interface ใช้ ABC กับ abstractmethod ทำหน้าที่เดียวกัน "
    "ถ้าถามเรื่อง overloading ตอบว่า Python ไม่มี method overloading แบบ Java ระบบนี้ใช้ overriding แทน "
    "และถ้าถามเรื่อง composition กับ aggregation Case ถือ CaseAssignment ไว้เป็นของตัวเองคือ composition "
    "ส่วน Schedule แค่ยืมรายการนัดมาตรวจ ไม่ได้เป็นเจ้าของ คือ aggregation ครับ"
)
title(s, "คำถามที่อาจถูกถาม", "สไลด์สำรอง เปิดเมื่อถูกถาม", num=19)
for i, (q, a) in enumerate([
    ("_status ยังเขียนทับได้ไหม?", "ได้ Python ไม่มี private จริง · _ คือข้อตกลง · property ไม่มี setter กันการแก้ผ่าน .status · ต้องการมากขึ้นใช้ __status (name mangling)"),
    ("ทำไมไม่มี interface?", "Python ไม่มีคีย์เวิร์ด interface · ใช้ ABC + @abstractmethod ทำหน้าที่เดียวกัน"),
    ("มี overloading ไหม?", "Python ไม่มี method overloading แบบ Java · ระบบนี้ใช้ overriding (เช่น home_url)"),
    ("composition vs aggregation?", "Case ถือ CaseAssignment เป็นของตัวเอง = composition · Schedule ยืมลิสต์นัดจาก repo = aggregation"),
]):
    x, y = 40 + (i % 2) * 450, 120 + (i // 2) * 175
    rect(s, x, y, 430, 160, fill=PANEL, line=LINE)
    text(s, x + 16, y + 12, 398, 28, q, size=17, bold=True, color=ACCENT)
    text(s, x + 16, y + 48, 398, 104, a, size=16)

# 20 ─ Backup B7: full case class diagram ────────────────────────────────────
s = new_slide(
    "ฝั่งคดีและตาราง ตรงกลางคือ Case เก็บสถานะและรายการมอบหมายไว้เป็น private คดีหนึ่งมี CaseAssignment ได้หลายรายการ แต่ละรายการผูกกับทนายหนึ่งคน "
    "ซ้ายล่างคือ Appointment เป็นคลาส abstract มีลูกสามชนิด นัดศาล นัดพบลูกความ และกำหนดยื่นเอกสาร "
    "นัดศาลเตือนล่วงหน้า 3 วัน นัดพบลูกความ 1 วัน กำหนดยื่น 15 วัน ตัวเลขต่างกันแต่เรียกเมธอดเดียวกัน "
    "ขวามือคือ Schedule ไม่ได้สร้างนัดเอง แค่ยืมรายการนัดจาก repository มาตรวจนัดชน เป็นความสัมพันธ์แบบ aggregation "
    "และทุกคลาสใน domain เขียนเป็น dataclass ส่วนสถานะคดีกับสถานะการมอบหมายเป็น enum ครับ"
)
title(s, "Case เป็นศูนย์กลาง ถือการมอบหมาย นัด และโน้ต (ฉบับเต็ม)", "CLASS DIAGRAM ฉบับเต็ม · สำรอง", num=20)
box(s, 40, 118, 270, 84, ["CaseAssignment (−status)", "accept() · decline()", "request_withdraw() · approve/reject()"],
    size=12)
box(s, 340, 118, 280, 84, ["Case (−status, −assignments)", "assign_lawyer() · advance_status()",
                           "lawyers() · lead_lawyer() · can_close()"], fill=HILITE, line=ACCENT, size=12)
box(s, 650, 118, 270, 84, ["Schedule", "add() · find_conflicts()", "day/week/month_view() · mark_done()"], size=12)
line(s, 310, 160, 340, 160)
text(s, 306, 160, 20, 20, "*", size=14, color=ACCENT)
text(s, 326, 160, 20, 20, "1", size=13, color=ACCENT)
text(s, 40, 204, 270, 22, "หลายรายการ ต่อ 1 Lawyer (สไลด์ 4)", size=12, color=ACCENT, align=PP_ALIGN.CENTER)
line(s, 785, 202, 785, 250, dash=True)
text(s, 790, 210, 130, 22, "◇ ยืมลิสต์นัด", size=12, color=ACCENT)
box(s, 40, 240, 270, 100, ["Appointment «abstract»", "reminder_lead_days()* · kind_label()*",
                           "can_reschedule()* · overlaps()", "reschedule() · cancel() · is_due_soon()"], size=12)
box(s, 40, 372, 270, 80, ["CourtHearing · ClientMeeting", "FilingDeadline",
                          ("นัดศาล 3 วัน · พบลูกความ 1 วัน · ยื่น 15 วัน", {"color": MUTED})],
    fill=HILITE, line=ACCENT, size=12)
line(s, 175, 372, 175, 340, head="triangle")
line(s, 480, 202, 480, 240)
text(s, 484, 204, 30, 20, "1", size=13, color=ACCENT)
text(s, 484, 222, 30, 20, "*", size=14, color=ACCENT)
box(s, 340, 240, 280, 70, ["CaseNote · CaseEvent", "คดี 1 : * (ผูกด้วย case_id)",
                           ("validate_text() · can_modify()", {"color": MUTED})], size=12)
box(s, 340, 325, 280, 55, ["Client", ("ลูกความ 1 : คดี * (case.client)", {"color": MUTED})], size=12)
box(s, 650, 250, 270, 100, ["«enum» · @dataclass", "CaseStatus 7 ค่า", "AssignmentStatus 4 ค่า",
                            ("domain ทุกคลาสเป็น @dataclass", {"color": MUTED})], size=12)
text(s, 340, 395, 580, 50, ["Case 1 : * มอบหมาย / นัด / โน้ต",
                            "Schedule ◇ นัด * (ยืมลิสต์นัดจาก repo มาตรวจ)"], size=13, color=ACCENT)
caption(s, 40, 478, 880, "อ้างอิง: domain/case.py · assignment.py · appointment.py · schedule.py")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_guard(out, stamp):
    if out.exists():
        built = stamp.read_text().strip() if stamp.exists() else None
        if sha256(out) != built:
            if "--force" not in sys.argv:
                sys.exit(f"{out.name} was edited after the last build (or has no build stamp). "
                         "Port the manual edits into this script, or rerun with --force to overwrite.")
            shutil.copy2(out, out.with_suffix(".pptx.bak"))
            print(f"backed up manual edits to {out.with_suffix('.pptx.bak').name}")


def save_subset(src, dst, keep):
    """Re-open src and keep only slide indices in keep; drop rels so no orphans remain."""
    sub = Presentation(str(src))
    lst = sub.slides._sldIdLst
    keep_set = set(keep)
    for i in sorted([i for i in range(len(lst)) if i not in keep_set], reverse=True):
        el = lst[i]
        rId = el.get(qn("r:id"))
        lst.remove(el)
        if rId:
            sub.part.drop_rel(rId)
    sub.save(dst)


MAIN_N = 12

check_guard(OUT_MAIN, STAMP_MAIN)
check_guard(OUT_BACKUP, STAMP_BACKUP)

slides = list(prs.slides._sldIdLst)
for el in slides:
    prs.slides._sldIdLst.remove(el)
for n in ORDER:
    prs.slides._sldIdLst.append(slides[n - 1])

import tempfile
tmp = Path(tempfile.mkstemp(suffix=".pptx")[1])
prs.save(tmp)
save_subset(tmp, OUT_MAIN, range(MAIN_N))
save_subset(tmp, OUT_BACKUP, range(MAIN_N, len(ORDER)))
tmp.unlink(missing_ok=True)
STAMP_MAIN.write_text(sha256(OUT_MAIN))
STAMP_BACKUP.write_text(sha256(OUT_BACKUP))
print(f"saved {OUT_MAIN} (12 slides)")
print(f"saved {OUT_BACKUP} ({len(ORDER) - MAIN_N} slides)")
