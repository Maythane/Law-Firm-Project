---
name: ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ
description: เครื่องมือภายในสำนักงานกฎหมาย — ทนายจัดการนัด/กำหนดยื่น ผู้จัดการมอบหมายคดี
colors:
  primary: "#5E35B1"
  primary-hover: "#4527A0"
  primary-surface: "#EDE7F6"
  accent-lavender: "#D1C4E9"
  neutral-bg: "#F7F5FC"
  neutral-ink: "#241C33"
  neutral-muted: "#6B6280"
  neutral-border: "#E8E3F2"
  neutral-chip: "#EFECF5"
  neutral-surface: "#FFFFFF"
  danger: "#E1523D"
  danger-surface: "#FBE3DF"
  danger-ink: "#A5341F"
  warning: "#D98A0B"
  warning-surface: "#FDF0D9"
  warning-ink: "#8A5A05"
typography:
  title:
    fontFamily: "Noto Sans Thai, system-ui, sans-serif"
    fontWeight: 600
  body:
    fontFamily: "Noto Sans Thai, system-ui, sans-serif"
    fontSize: "1rem"   # 1rem = 15px (--pico-font-size: 93.75%)
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Noto Sans Thai, system-ui, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 600
rounded:
  sm: "4px"
  md: "0.5rem"
  lg: "0.75rem"
  pill: "999px"
spacing:
  sm: "0.35rem"
  md: "0.75rem"
  lg: "1.2rem"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
  chip-default:
    backgroundColor: "{colors.primary-surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.pill}"
    padding: "0.15rem 0.6rem"
  chip-neutral:
    backgroundColor: "{colors.neutral-chip}"
    textColor: "#4A4260"
    rounded: "{rounded.pill}"
    padding: "0.15rem 0.6rem"
  chip-danger:
    backgroundColor: "{colors.danger-surface}"
    textColor: "{colors.danger-ink}"
    rounded: "{rounded.pill}"
    padding: "0.15rem 0.6rem"
  badge-count:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.pill}"
  badge-count-muted:
    backgroundColor: "{colors.neutral-border}"
    textColor: "{colors.neutral-muted}"
    rounded: "{rounded.pill}"
  card-surface:
    backgroundColor: "{colors.neutral-surface}"
    rounded: "{rounded.lg}"
    padding: "1.1rem 1.25rem"
---

# Design System: ระบบผู้ช่วยจัดการคดีและตารางนัดหมายสำหรับทนายความ

## 1. Overview

**Creative North Star: "The Case File"**

ระบบนี้ให้ความรู้สึกเหมือนเปิดแฟ้มคดีที่จัดเรียงไว้อย่างดี ไม่ใช่แดชบอร์ดขายของหรือแอปสไตล์สตาร์ทอัป พื้นหลังลาเวนเดอร์อ่อนแทนกระดาษ การ์ดสีขาวแทนแฟ้มย่อยแต่ละใบ สีม่วงเข้ม (`#5E35B1`) ใช้เป็นตัวบอกว่า "ตรงนี้กดได้/ต้องลงมือ" เท่านั้น — ปุ่มหลัก, ลิงก์, เมนูที่เลือกอยู่, badge จำนวนคดีค้าง — ไม่ใช่สีตกแต่งเกลื่อนหน้า

ปฏิเสธความรู้สึกแบบซอฟต์แวร์ enterprise สีเทาทึมๆ (ERP/ระบบราชการเก่า) โดยไม่ต้องพึ่งไอคอน/ภาพประกอบหรือ motion หวือหวา — ใช้แค่จังหวะสีที่ตัดกันชัดระหว่างพื้นหลังลาเวนเดอร์กับพื้นผิวขาว ช่องว่างที่เพียงพอ และมุมโค้งนุ่มทั่วระบบ (0.5-0.75rem) แทน

**Key Characteristics:**
- โทนม่วง/ลาเวนเดอร์เดียว ไม่มีสีคู่แข่งแย่งความสนใจ
- แบนราบ (ไม่มี shadow เลยทั้งระบบ) ใช้พื้นหลัง + เส้นขอบบางแทนความลึก
- ความหนาแน่นของข้อมูลสูงตามธรรมชาติของงานกฎหมาย (ตาราง ปฏิทิน รายการ) แต่จัดจังหวะด้วยตารางเรียบ (เส้นแบ่งแถวบางเส้นเดียว ไม่มีกล่องหุ้ม) การ์ดสงวนไว้ให้ของที่เป็น "แผ่น" จริง (นัดวันนี้ ปฏิทิน แผงข้าง)
- ฟอนต์เดียวทั้งระบบ (Noto Sans Thai) ไม่ผสมหลายฟอนต์

## 2. Colors

พาเลตเดียว: ม่วงเข้มเป็นสีหลัก ลาเวนเดอร์อ่อนเป็นพื้นผิว แดง/เหลืองอำพันสงวนไว้เฉพาะสถานะเร่งด่วนเท่านั้น

### Primary
- **Chambers Purple** (`#5E35B1`): ปุ่มหลัก, ลิงก์, ข้อความของเมนูที่เลือกอยู่, ตัวเลขบนการ์ดแจ้งเตือน, badge จำนวนคดีรอตอบรับ
- **Chambers Purple Hover** (`#4527A0`): สถานะ hover/active ของทุกอย่างที่ใช้ Chambers Purple

### Neutral
- **Paper Lavender** (`#F7F5FC`): พื้นหลังของทั้งหน้า มีอยู่เพื่อให้การ์ดสีขาวลอยขึ้นมาโดยไม่ต้องใช้ shadow
- **Soft Chambers** (`#EDE7F6`): พื้นผิวรอง — พื้น chip ปกติ (นัดศาล, ทนายหลัก), พื้นเมนู sidebar ที่เลือก/hover, แท็บที่เลือก, วันนี้ในปฏิทิน
- **Chambers Lavender** (`#D1C4E9`): เส้นขอบปุ่มรอง (outline), เส้นประของสถานะว่าง, เส้นแนวตั้งของ timeline
- **Neutral Chip** (`#EFECF5`): พื้น chip กลาง ๆ (นัดพบลูกความ, สถานะคดี, เลขคดี) และพื้นแถบความคืบหน้า
- **Ink Plum** (`#241C33`): สีตัวอักษรหลักทั้งระบบ — ดำอมม่วงเล็กน้อย ไม่ใช่ดำสนิท
- **Filing Muted** (`#6B6280`): ตัวอักษรรอง (เวลา, คำอธิบายใต้หัวข้อ, label ที่ไม่ต้องการความสนใจ)
- **Folder Line** (`#E8E3F2`): เส้นขอบ/เส้นแบ่งทุกจุด, พื้นหลัง badge ตอนไม่มีรายการค้าง (สถานะ "0")
- **Case Surface** (`#FFFFFF`): พื้นหลังการ์ด/panel ทุกชนิด

### Named Rules (optional, powerful)
**The One Accent Rule.** สีม่วงเข้ม (`#5E35B1`) ปรากฏเฉพาะสิ่งที่กดได้หรือต้องลงมือ (ปุ่ม ลิงก์ เมนูที่เลือก ตัวเลขค้าง) — พื้นผิวทั้งหมดเป็นขาว/เทาอมม่วงอ่อน ลาเวนเดอร์เป็นพื้นอ่อนของ chip/hover เท่านั้น ไม่ใช่สีตกแต่งหัวข้อหรือพื้นหลังส่วนหัว

### Tertiary — สถานะเร่งด่วน (ใช้เฉพาะ badge/chip นับวัน ไม่ใช้เป็นสีตกแต่ง)
- **Filing Red** (`#E1523D` / พื้นหลัง `#FBE3DF` ตัวอักษร `#A5341F`): กำหนดยื่นเอกสาร, คำขอถอนตัว, เกินเกณฑ์ภาระงาน, แถบ error/เตือน, รายการเตือนที่เหลือ ≤1 วันหรือเลยกำหนดแล้ว
- **Caution Amber** (`#D98A0B` / พื้นหลัง `#FDF0D9` ตัวอักษร `#8A5A05`): รายการเตือนที่ยังมีเวลาเหลือมากกว่า 1 วัน

## 3. Typography

**Body Font:** Noto Sans Thai (โหลดจาก Google Fonts) with fallback `system-ui, sans-serif`
**Display/Label Font:** ฟอนต์เดียวกัน — ไม่แยกฟอนต์ display ต่างหาก

**Character:** ฟอนต์เดียวทั้งระบบตามธรรมชาติของ product UI — ไม่ต้องจับคู่ฟอนต์เพื่อสร้างบุคลิก อ่านง่ายทั้งภาษาไทยและอังกฤษ/ตัวเลขปนกัน (เลขคดีอย่าง "35/2568" ต้องอ่านง่ายเท่าชื่อคดีภาษาไทย)

### Hierarchy
- **Title** (600): หัวข้อหน้า h2 1.4rem (ในหัวหน้ามาตรฐาน), h3 1.05rem
- **Body** (400, 1rem = 15px, line-height 1.5): เนื้อหาทั่วไป ตัวเลขในตารางเป็น tabular
- **Meta** (400, ~0.75-0.85rem, สี Filing Muted): บรรทัดรองใต้ชื่อหน้า/แถวรายการ เช่น "ศาลแพ่ง · มอบหมายโดย ผู้จัดการสมศักดิ์ · 07/09/2569" และหัวตาราง (600)
- **Label** (600, 0.72rem): ตัวอักษรบน chip/badge ทั้งหมด ป้ายชื่อช่องกรอกเป็น 0.85rem (600)

### Named Rules
**The No Display Font Rule.** ไม่มีฟอนต์ display แยกจากฟอนต์เนื้อหา แม้แต่หัวข้อหน้าใหญ่ที่สุดก็ใช้ Noto Sans Thai น้ำหนัก 600 แบบเดียวกัน — ตรงกับ product register ที่ไม่ต้องการความหวือหวาทางการพิมพ์

## 4. Elevation

ระบบนี้ **แบนราบทั้งหมด ไม่มี box-shadow แม้แต่จุดเดียว**ในทั้งระบบ ความลึกสื่อผ่านการตัดกันของพื้นหลังลาเวนเดอร์ (Paper Lavender) กับพื้นผิวการ์ดสีขาว (Case Surface) และเส้นขอบบาง 1px (Folder Line) เท่านั้น

### Named Rules
**The Flat Ledger Rule.** ไม่มี shadow ไม่มี glassmorphism ความแตกต่างของ "ชั้น" มาจากสีพื้นหลังที่ต่างกันเท่านั้น — ให้ความรู้สึกเหมือนแฟ้มเอกสารวางเรียงบนโต๊ะ ไม่ใช่การ์ดลอยในอากาศ

## 5. Components

### Buttons
- **Shape:** มุมโค้ง 0.5rem เหมือนกันทุกปุ่ม น้ำหนักตัวอักษร 600
- **Primary:** พื้นหลัง Chambers Purple (`#5E35B1`) ตัวอักษรขาว หนึ่งหน้ามีปุ่มหลักได้หนึ่งปุ่มที่หัวหน้า (เช่น "+ เพิ่มนัด", "+ เพิ่มคดีใหม่") ยกเว้น action หลักในแผงเฉพาะ (เช่น เลื่อนสถานะคดี)
- **Secondary (outline):** พื้นโปร่ง เส้นขอบ Chambers Lavender ตัวอักษร Chambers Purple — ใช้กับ action รอง ("ไม่รับ", "ปิด", "ดูคดี", ปุ่มเดินเดือน) hover เติมพื้น Soft Chambers
- **Hover (primary):** พื้นหลังเข้มขึ้นเป็น Chambers Purple Hover (`#4527A0`) ไม่มี transform/scale

### Chips
- **Style:** ทรงเม็ดยา (rounded pill, 999px) ตัวอักษรเล็กหนา (0.7rem/700) ไม่มีเส้นขอบ
- **State:** สื่อความหมาย ไม่ใช่สถานะเลือก/ไม่เลือก — ปกติ (นัดศาล, ทนายหลัก, เปิดใช้งาน) = Soft Chambers พื้นอ่อนตัวอักษรม่วง, กลาง ๆ (นัดพบลูกความ, สถานะคดี) = Neutral Chip, เร่งด่วน/ผิดปกติ (กำหนดยื่นเอกสาร, ขอถอนตัว, เกินเกณฑ์) = Filing Red อ่อน (`chip-danger`)

### Cards / Containers
- **Corner Style:** มุมโค้ง 0.75rem (`card-surface`)
- **Background:** Case Surface (`#FFFFFF`) บนพื้น Paper Lavender เสมอ
- **Shadow Strategy:** ไม่มี — ดูหัวข้อ Elevation
- **Border:** เส้นขอบ 1px สี Folder Line ไม่มีแถบสีข้างการ์ด — ชนิด/ความหมายสื่อด้วย chip ในการ์ดแทน
- **Tables & rows:** ตารางและแถวรายการ (item-card) ไม่มีกล่องหุ้ม ใช้เส้นแบ่งแถวบางเส้นเดียว หัวตารางตัวเล็กสีจาง การ์ดใช้กับแผ่นที่เป็นหน่วยเดียว (นัดวันนี้, ปฏิทิน, แผงข้างหน้าคดี, การ์ดตัวเลข dashboard)
- **Internal Padding:** 1.1-1.25rem สำหรับ panel, 0.8-1rem สำหรับการ์ดนัด
- **Stat card:** การ์ดตัวเลข dashboard manager — ตัวเลขใหญ่ Chambers Purple (0 = จาง) ป้ายรองสี Filing Muted กดแล้วไปที่รายการของประเภทนั้น
- **Empty state:** กรอบเส้นประ Chambers Lavender ข้อความจางกึ่งกลางในพื้นที่เดียวกับรายการ
- **Banner:** แถบ error/เตือนสี Filing Red อ่อน ไม่มีเส้นขอบ

### Badge (Signature Component)
ตัวเลขนับจำนวนคดีรอตอบรับที่ sidebar (BL-36) — วงกลมเม็ดยา สีม่วงทึบตัวอักษรขาวเมื่อมีรายการ (`badge-count`), เปลี่ยนเป็นสีเทา Folder Line ตัวอักษร Filing Muted เมื่อไม่มีรายการ (`badge-count-muted`) **แสดงตัวเลขเสมอทั้งสองสถานะ ไม่ซ่อน** — เป็นเจตนาการออกแบบหลักของ badge นี้ ไม่ใช่รายละเอียดเล็กๆ

### Navigation
- **Style:** sidebar ซ้ายกว้าง 232px พื้นขาว, แถวเมนูเป็นลิงก์เต็มความกว้าง มุมโค้ง 0.5rem ไม่มีจุดนำหน้า
- **Default:** ตัวอักษร Filing Muted
- **Active/Hover:** พื้นหลัง Soft Chambers ตัวอักษร Chambers Purple น้ำหนัก 600
- **Mobile:** ต่ำกว่า 860px sidebar หายไป สลับเป็นแถบบน (ชื่อระบบ + ปุ่ม "เมนู") ที่เป็น `<details>` เปิดรายการเมนูเดียวกับ sidebar พร้อมชื่อผู้ใช้/แก้ไขผู้ใช้/ออกจากระบบ ด้วย HTML+CSS ล้วน ไม่มี JavaScript
- **หัวหน้ามาตรฐาน (`.page-head`):** ชื่อหน้า (ซ้าย) + บรรทัดรองบอกบริบท + ปุ่มหลักหนึ่งปุ่ม (ขวา)

## 6. Layout

ระบบนี้ไม่ใช้ grid ระบบคอลัมน์ (เช่น 12-column) — โครงหน้าเป็น **two-region shell** คงที่: sidebar + พื้นที่เนื้อหา แล้วแต่ละหน้าจัดองค์ประกอบภายในเองตามความจำเป็น

### Shell
- **Sidebar:** กว้างคงที่ 232px, พื้นขาว, `position: sticky` ยึดกับจอเสมอแม้เนื้อหาจะยาวเกิน viewport (ไม่ยืดตามความสูงเนื้อหา)
- **เนื้อหา:** พื้นที่ที่เหลือ (`flex: 1`) กว้างสูงสุด 1100px ไม่งั้นบรรทัดยาวเกินไปอ่านยากบนจอกว้าง — เว้นระยะขอบบน 2rem ให้หายใจก่อนเจอหัวข้อหน้า
- **Breakpoint เดียว** ที่ 860px — ต่ำกว่านี้ sidebar หายไปทั้งหมด สลับเป็นแถบบนพร้อมเมนู `<details>` ด้วย CSS media query ล้วนๆ ไม่มี JavaScript ควบคุม breakpoint

### Composition Patterns
- **1 คอลัมน์ (ค่าเริ่มต้น):** การ์ด/panel/ตารางเรียงต่อกันในแนวตั้งเต็มความกว้างเนื้อหา — ใช้กับหน้าส่วนใหญ่ (รายการ, ฟอร์ม, dashboard สถิติ)
- **หน้าฟอร์ม (`.form-page`):** กรอบกว้างสูงสุด 640px กึ่งกลาง ป้ายชื่ออยู่บนช่อง ช่องที่เกี่ยวข้องจัดคู่ (`.grid`) ปุ่มหลักชิดซ้ายพร้อมลิงก์ "ยกเลิก" (`.form-actions`)
- **หน้าคดี (`.case-layout`):** เนื้อหาซ้าย (สรุปคดี → นัด → โน้ต) + แผงข้าง 320px (จัดการคดี, ทนายที่รับผิดชอบ, ประวัติพับได้) ยุบเป็นคอลัมน์เดียวต่ำกว่า 960px เนื้อหาก่อนแผงข้าง
- **Dashboard manager:** การ์ดตัวเลข 3 ใบ → คิว "รอดำเนินการ" (แถวมี chip ชนิด + ปุ่ม action) → ตารางภาระงานเต็มความกว้าง
- **เนื้อหา + panel ข้าง (`.cols-2`):** เนื้อหาหลัก `1fr` + panel ข้าง `300px` คงที่ — ใช้ตอนมีข้อมูลรองที่ควรเห็นพร้อมกันแบบไม่ต้องเลื่อนหา (เช่น ปฏิทิน + แผง "ใกล้ครบกำหนด") ยุบเป็นคอลัมน์เดียวอัตโนมัติต่ำกว่า 960px
- **ฟอร์ม 2 ช่องต่อแถว (`.grid`):** ใช้กับฟอร์มที่มีฟิลด์คู่ที่สัมพันธ์กัน (เช่น เพิ่มผู้ใช้ใหม่) — ไม่ใช้กับฟอร์มสั้น (login, แก้ไขบัญชีตัวเอง) ที่ให้ฟิลด์เรียงคอลัมน์เดียวแทน เพราะฟอร์มสั้นอยู่แล้วการแบ่ง 2 คอลัมน์ไม่ได้ช่วยอะไร

### Spacing
ไม่ใช่ระบบหน่วยเดียวตายตัว (ไม่ใช่ multiples ของ 8px) — ปรับตามบริบทของแต่ละ component: ช่องไฟภายในเล็ก (label/chip) ใช้ `0.2-0.4rem`, ช่องไฟภายในการ์ด/ปุ่มทั่วไปใช้ `0.6-0.9rem` (ตรงกับ `spacing.sm/md` ใน frontmatter), ระยะห่างระหว่างกล่อง/section ใช้ `1-1.3rem` (`spacing.lg`) — ยึดตามความรู้สึก "กระทัดรัดแบบงานเอกสาร" มากกว่าสูตรตายตัว ตรงข้ามกับ dashboard สไตล์ data-viz ที่มักใช้ 8px grid เข้มงวด เพราะ product register ของระบบนี้คือ "แฟ้มคดี" ไม่ใช่ analytics dashboard

## 7. Do's and Don'ts

### Do:
- **Do** ใช้สีม่วง Chambers Purple (`#5E35B1`) เฉพาะสิ่งที่กดได้/ต้องลงมือ ไม่ใช่ตกแต่งพื้นหลังหรือหัวข้อ (The One Accent Rule)
- **Do** ให้พื้นหลังหน้าเป็น Paper Lavender เสมอ แล้วให้การ์ดขาวลอยขึ้นมาด้วยสีเท่านั้น ไม่ใช้ shadow (The Flat Ledger Rule)
- **Do** สื่อชนิด/ความเร่งด่วนของรายการด้วย chip ในแถว ไม่ใช้สีพื้นหรือแถบข้างการ์ด
- **Do** ใช้หัวหน้ามาตรฐาน (`.page-head`) ทุกหน้า และหน้าฟอร์มใช้ `.form-page` ทั้งหมด
- **Do** แสดง badge ตัวเลขเสมอทั้งสองสถานะ (มี/ไม่มีรายการ) ไม่ปล่อยให้ "ไม่มี badge" ต้องตีความเอง
- **Do** ใช้ Noto Sans Thai ตัวเดียวทั้งระบบ ไม่จับคู่ฟอนต์

### Don't:
- **Don't** เพิ่มสีที่สามเข้ามาแย่งพื้นที่กับม่วง/แดง/อำพัน — ระบบนี้เป็น Restrained palette ตาม product register
- **Don't** ทำให้แอปดูเหมือนซอฟต์แวร์ enterprise สีเทาทึมๆ (anti-reference จาก PRODUCT.md) — อย่าลดสีลงเป็นเทาเพื่อ "ดูเป็นทางการ"
- **Don't** เพิ่ม box-shadow, glassmorphism, หรือ gradient เข้ามาสร้างความลึก — ขัดกับ The Flat Ledger Rule (รวม dialog และเมนูมือถือ ใช้เส้นขอบบางแทน)
- **Don't** ใส่แถบสีหนาที่ขอบข้างของการ์ดหรือแถว (side-stripe) — เลิกใช้แล้วในการยกเครื่อง UI (BL-41)
- **Don't** ใช้สีแดง (`#E1523D`) หรือเหลืองอำพัน (`#D98A0B`) กับอะไรที่ไม่ใช่สถานะเร่งด่วน/เลยกำหนด
- **Don't** เพิ่ม motion ที่ไม่สื่อสถานะ (ไม่มี orchestrated animation ในระบบนี้เลยตามธรรมชาติของ product register)
- **Don't** เปลี่ยนไปธีมมืด/สีนีออน (cyan, เขียวมะนาว ฯลฯ) หรือใช้ font ตัวเลขแบบ monospace ขนาดใหญ่แบบ data-viz dashboard — ต่อให้มีเอกสารสไตล์อื่นมาอ้างอิง (เช่น dashboard ตรวจสอบไฟฟ้าที่เป็น dark mode) ก็ใช้แค่ "รูปแบบการจัดหมวดเอกสาร" เป็นไอเดีย ไม่ใช่จานสีหรือ typography — CI ของระบบนี้คือม่วง/ขาวเสมอ
