# CLAUDE.md — ระบบตรวจสอบคลังอุปกรณ์ (Supply Requisition Inventory System)

## 📌 Project Overview

ระบบ Web Application สำหรับตรวจสอบและจัดการคลังอุปกรณ์ โดยใช้การสแกน Barcode (UUID) เพื่อยืนยันและแก้ไขข้อมูลอุปกรณ์

**Tech Stack:**
- Package Manager: **uv** (แทน pip/venv)
- Backend: Python Flask + Psycopg2 / Flask-SQLAlchemy
- Database: PostgreSQL
- Frontend: Jinja2 Templates + TailwindCSS (CDN)
- Barcode Scanner: HTML5-QRCode (JavaScript Library)
- Barcode Generator: `python-barcode` + `Pillow`
- PDF Generator: `FPDF2` + Font TH Sarabun New

---

## 🗄️ Database Schema

### ตาราง `supply_requisitions`

```sql
CREATE TABLE supply_requisitions (
    sequence_no            SERIAL PRIMARY KEY,
    barcode_uuid           UUID NOT NULL DEFAULT gen_random_uuid(),
    item_number            VARCHAR(50),
    original_item          VARCHAR(255),
    requisition_item       VARCHAR(255),
    item_name              VARCHAR(255),
    issuing_unit           VARCHAR(100),
    requisition_unit       VARCHAR(100),
    issued_to              VARCHAR(100),
    supply_control_section VARCHAR(100),
    supply_borrowing_unit  VARCHAR(100),
    status                 VARCHAR(50),
    verified               BOOLEAN DEFAULT FALSE,
    quantity               NUMERIC(10,2),
    unit_of_measure        VARCHAR(50),
    remarks                TEXT,
    supply_type            VARCHAR(100),
    has_requisition        BOOLEAN,
    requisition_number     VARCHAR(100),
    transaction_date       DATE,
    responsible_person     VARCHAR(100),
    responsible_phone      VARCHAR(20),
    last_verified_by       INTEGER REFERENCES users(id),
    last_verified_at       TIMESTAMP
);

-- Index สำหรับสแกน Barcode
CREATE UNIQUE INDEX idx_barcode_uuid ON supply_requisitions (barcode_uuid);
```

### ตาราง `users`

```sql
CREATE TABLE users (
    id             SERIAL PRIMARY KEY,
    username       VARCHAR(100) UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    phone          VARCHAR(20),
    role           VARCHAR(20) DEFAULT 'user',   -- 'admin' | 'user'
    is_approved    BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT NOW()
);
```

---

## 🏗️ โครงสร้างโปรเจกต์

```
project/
├── pyproject.toml            # uv project config (แทน requirements.txt)
├── uv.lock                   # uv lockfile (auto-generated)
├── .python-version           # Python version pin
├── .env                      # Environment variables
├── app.py                    # Flask entry point
├── config.py                 # Database & App config
├── decorators.py             # @login_required, @admin_required
├── models/
│   ├── __init__.py
│   ├── user.py               # User model
│   └── supply.py             # SupplyRequisition model
├── routes/
│   ├── __init__.py
│   ├── auth.py               # Login, Register, Reset Password
│   ├── admin.py              # Admin dashboard, approve users
│   ├── scanner.py            # Barcode scan & verification
│   ├── labels.py             # PDF Label generation  ← ใหม่
│   └── dashboard.py          # Overview dashboard
├── templates/
│   ├── base.html             # Base layout (TailwindCSS CDN)
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── reset_password.html
│   ├── admin/
│   │   └── dashboard.html    # Approve pending users
│   ├── scanner/
│   │   └── scan.html         # Camera scan + verify/edit form
│   ├── inventory/
│   │   └── list.html         # รายการพร้อม Checkbox + ปุ่ม Generate Labels  ← ใหม่
│   └── dashboard/
│       └── index.html        # Overview cards + recent table
├── static/
│   ├── fonts/
│   │   └── THSarabunNew.ttf  # Font ภาษาไทยสำหรับ FPDF2  ← ใหม่
│   └── js/
│       └── scanner.js        # HTML5-QRCode init script
└── utils/
    └── barcode_gen.py        # Helper: สร้าง barcode image จาก UUID  ← ใหม่
```

---

## 🔐 Phase 1 — Authentication (auth.py)

### Prompt สำหรับ Claude:

> ช่วยเขียน Route และ HTML Template สำหรับส่วนการจัดการผู้ใช้งานใน Flask:
>
> - **หน้า Register**: รับค่า Username, Password และเบอร์โทรศัพท์
> - **หน้า Admin Dashboard**: แสดงรายชื่อผู้สมัครที่รอการอนุมัติ (`is_approved = False`) และมีปุ่ม 'Approve' เพื่อเปลี่ยนสถานะเป็น `True`
> - **Middleware/Decorator**: เขียน `@admin_required` เพื่อจำกัดสิทธิ์ให้เฉพาะ Admin เท่านั้นที่เข้าถึงหน้าอนุมัติได้

### ฟีเจอร์:
- `POST /auth/register` — สมัครสมาชิก (`is_approved = False` เป็น Default)
- `POST /auth/login` — เข้าสู่ระบบ (ตรวจสอบ `is_approved` ก่อนอนุญาต)
- `GET/POST /auth/reset-password` — รีเซ็ตรหัสผ่าน
- `GET /admin/users` — รายชื่อผู้รอการอนุมัติ (Admin only)
- `POST /admin/approve/<user_id>` — อนุมัติสมาชิก

### Decorators (decorators.py):
```python
@login_required     # ตรวจสอบว่า Login แล้ว
@admin_required     # ตรวจสอบว่าเป็น Admin (role == 'admin')
```

---

## 📷 Phase 2 — Barcode Scanner & Verification (scanner.py)

### Prompt สำหรับ Claude:

> ช่วยเขียนหน้า 'Check-in Equipment' โดยใช้ HTML5-QRCode library สำหรับสแกนบาร์โค้ดผ่านกล้องมือถือ:
>
> - เมื่อสแกนได้ `barcode_uuid` ให้ส่งค่าไปยัง Route `/api/get_item/<uuid>` ด้วย AJAX/Fetch
> - แสดงข้อมูลอุปกรณ์ใน Form (Item Name, Quantity, Unit, etc.)
> - มีปุ่ม **'ยืนยันข้อมูลถูกต้อง'** (Update `verified = True`) และปุ่ม **'แก้ไขข้อมูล'**
> - เมื่อบันทึก ให้ Update ข้อมูลใน `supply_requisitions` พร้อมเก็บ `last_verified_by` และ `last_verified_at`

### Routes:
```
GET  /scanner                    — หน้าสแกน Barcode
GET  /api/get_item/<uuid>        — ดึงข้อมูลจาก UUID (JSON Response)
POST /api/verify/<uuid>          — ยืนยันข้อมูล (verified = True)
POST /api/update/<uuid>          — แก้ไขและบันทึกข้อมูล
```

### Logic การ Verify:
```sql
UPDATE supply_requisitions
SET
    verified         = TRUE,
    last_verified_by = :user_id,
    last_verified_at = NOW()
WHERE barcode_uuid = :uuid;
```

---

## 📊 Phase 3 — Dashboard (dashboard.py)

### Prompt สำหรับ Claude:

> ช่วยเขียนหน้า Dashboard สำหรับแสดงภาพรวมของคลังอุปกรณ์:
>
> - **Card สรุปตัวเลข**: จำนวนอุปกรณ์ทั้งหมด, ตรวจสอบแล้ว (`verified = True`), ยังไม่ได้ตรวจสอบ
> - **ตารางรายการล่าสุด 10 รายการ**: ชื่ออุปกรณ์, ผู้ตรวจสอบ, วันที่
> - ใช้ TailwindCSS ทำตารางให้สะอาดตาและ Mobile Responsive

### Query หลัก:
```sql
-- Summary Cards
SELECT
    COUNT(*)                            AS total,
    COUNT(*) FILTER (WHERE verified)    AS verified_count,
    COUNT(*) FILTER (WHERE NOT verified) AS unverified_count
FROM supply_requisitions;

-- Recent 10 verified items
SELECT
    sr.item_name,
    sr.quantity,
    sr.unit_of_measure,
    u.username      AS verified_by,
    sr.last_verified_at
FROM supply_requisitions sr
LEFT JOIN users u ON sr.last_verified_by = u.id
WHERE sr.verified = TRUE
ORDER BY sr.last_verified_at DESC
LIMIT 10;
```

---

## ⚙️ config.py

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/supply_db'
    )
    DEBUG = os.environ.get('DEBUG', True)
```

---

## 📦 Phase 4 — PDF Label Printing (labels.py)

### Prompt สำหรับ Claude:

> ช่วยเขียนฟีเจอร์สำหรับเลือกรายการอุปกรณ์หลายๆ รายการเพื่อสร้างเป็นไฟล์ PDF สำหรับสั่งพิมพ์บาร์โค้ด (Label Printing):
>
> 1. **หน้ารายการ (Inventory List):** เพิ่ม Checkbox หน้าแต่ละแถวในตาราง `supply_requisitions` เพื่อให้ผู้ใช้เลือกรายการที่ต้องการพิมพ์ได้หลายอันพร้อมกัน และมีปุ่ม 'สร้างใบสติกเกอร์บาร์โค้ด (Generate Labels)' ที่จะส่ง List ของ `sequence_no` หรือ `barcode_uuid` ไปยัง Route สำหรับสร้าง PDF
> 2. **การสร้างบาร์โค้ด (Backend):** ใช้ Library `python-barcode` + `Pillow` ในการสร้าง Barcode Image จาก `barcode_uuid` และใช้ `FPDF2` สำหรับการสร้างไฟล์ PDF
> 3. **รูปแบบเลย์เอาต์ใน PDF (Label Layout):** จัดเรียงแบบ Grid 3 คอลัมน์ต่อหน้า A4 แต่ละ Label แสดง: รูปภาพบาร์โค้ด, เลขที่อุปกรณ์ (`item_number`), รายการ (`requisition_item`), หน่วยงานที่จ่าย (`issuing_unit`) และใช้ Font TH Sarabun New รองรับภาษาไทย
> 4. **ผลลัพธ์:** ระบบ Generate PDF และเปิดใน Browser Tab ใหม่เพื่อสั่งพิมพ์ได้ทันที

### Routes:
```
GET  /inventory               — หน้ารายการพร้อม Checkbox
POST /labels/generate         — รับ list of UUIDs → สร้าง PDF → stream กลับ
```

### Backend Flow (labels.py):
```python
# 1. รับ UUID list จาก POST body
# 2. Query ข้อมูลจาก DB
# 3. วนลูปสร้าง barcode image ต่อ item
# 4. วาง label ลงใน PDF grid (3 คอลัมน์ × N แถว)
# 5. Stream PDF กลับด้วย send_file(..., as_attachment=False)

from fpdf import FPDF
import barcode
from barcode.writer import ImageWriter
import io

def generate_barcode_image(uuid_str: str) -> bytes:
    """สร้าง barcode PNG จาก UUID string"""
    code128 = barcode.get('code128', uuid_str, writer=ImageWriter())
    buffer = io.BytesIO()
    code128.write(buffer)
    return buffer.getvalue()
```

### Label Layout บน A4 (3 คอลัมน์):
```
┌─────────────────────────────────────┐  A4 Portrait
│  [Label]  [Label]  [Label]          │
│  [Label]  [Label]  [Label]          │
│  [Label]  [Label]  [Label]          │
│  ...                                │
└─────────────────────────────────────┘

แต่ละ Label (~62mm × 40mm):
┌──────────────────┐
│ ▐▌▌▌▐▌▐▌▐▌▌▌▐▌  │  ← Barcode Image
│ 1234-ABCD-UUID   │  ← UUID (ย่อ)
│ เลขที่: XX-001   │  ← item_number
│ รายการ: ชื่อสป.  │  ← requisition_item
│ หน่วย: กองพัน   │  ← issuing_unit
└──────────────────┘
```

### utils/barcode_gen.py:
```python
import barcode
from barcode.writer import ImageWriter
import io

def make_barcode_png(uuid_str: str) -> bytes:
    writer = ImageWriter()
    code = barcode.get('code128', uuid_str, writer=writer)
    buf = io.BytesIO()
    code.write(buf, options={
        'module_width': 0.8,
        'module_height': 8.0,
        'quiet_zone': 2.0,
        'font_size': 6,
        'text_distance': 2.0,
    })
    buf.seek(0)
    return buf.read()
```

### Flask Route (ส่ง PDF กลับ):
```python
@labels_bp.route('/labels/generate', methods=['POST'])
@login_required
def generate_labels():
    uuids = request.json.get('uuids', [])
    items = db.session.execute(
        select(SupplyRequisition).where(
            SupplyRequisition.barcode_uuid.in_(uuids)
        )
    ).scalars().all()

    pdf_bytes = build_label_pdf(items)   # สร้าง PDF
    buf = io.BytesIO(pdf_bytes)
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=False,             # เปิดใน Tab ใหม่
        download_name='labels.pdf'
    )
```

### Frontend (inventory/list.html) — Checkbox + Submit:
```javascript
document.getElementById('btn-generate').addEventListener('click', () => {
  const checked = [...document.querySelectorAll('.item-check:checked')]
    .map(el => el.dataset.uuid);

  if (checked.length === 0) {
    alert('กรุณาเลือกอุปกรณ์อย่างน้อย 1 รายการ');
    return;
  }

  fetch('/labels/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uuids: checked })
  })
  .then(res => res.blob())
  .then(blob => {
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');   // เปิด PDF Tab ใหม่
  });
});
```

---

## ⚙️ uv — Package Manager Setup

โปรเจกต์นี้ใช้ **uv** แทน pip/venv เพื่อความเร็วและ reproducibility

### ติดตั้ง uv:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### เริ่มต้น Project:
```bash
uv init supply-inventory
cd supply-inventory
uv python pin 3.12          # กำหนด Python version → สร้าง .python-version
```

### เพิ่ม Dependencies:
```bash
uv add flask
uv add flask-sqlalchemy
uv add flask-login
uv add psycopg2-binary
uv add python-dotenv
uv add python-barcode[images]   # รวม Pillow
uv add fpdf2
```

### pyproject.toml (auto-generated โดย uv):
```toml
[project]
name = "supply-inventory"
version = "0.1.0"
description = "ระบบตรวจสอบคลังอุปกรณ์"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.1",
    "flask-sqlalchemy>=3.1",
    "flask-login>=0.6",
    "psycopg2-binary>=2.9",
    "python-dotenv>=1.0",
    "python-barcode[images]>=0.15",
    "fpdf2>=2.8",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "ruff>=0.5",
]
```

### รันโปรเจกต์:
```bash
uv run flask --app app run --debug       # Development
uv run flask --app app run --host 0.0.0.0 --port 5000  # LAN Access
```

### คำสั่ง uv ที่ใช้บ่อย:
```bash
uv sync                 # ติดตั้ง dependencies จาก uv.lock
uv add <package>        # เพิ่ม package (อัปเดต pyproject.toml + uv.lock อัตโนมัติ)
uv remove <package>     # ลบ package
uv run <command>        # รัน command ใน virtual env
uv lock --upgrade       # อัปเดต uv.lock ทุก package
```

> **ไม่ต้อง** `source .venv/bin/activate` — ใช้ `uv run` แทนได้เลย

---

## ⚙️ config.py

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/supply_db'
    )
    DEBUG = os.environ.get('DEBUG', True)
```

### .env (ไม่ commit ลง Git):
```env
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/supply_db
DEBUG=true
```

---

## 🚀 ลำดับการพัฒนา (Development Order)

| ลำดับ | Phase | สิ่งที่ต้องทำ |
|-------|-------|--------------|
| 1 | Setup | `uv init` → เพิ่ม dependencies → สร้าง DB → รัน SQL Schema |
| 2 | Auth | Register → Login → Admin Approve |
| 3 | Scanner | สแกน UUID → แสดงข้อมูล → Verify/Edit |
| 4 | Dashboard | Cards + ตารางล่าสุด |
| 5 | Labels | Inventory List + Checkbox → Generate PDF Barcode Labels |
| 6 | Polish | Mobile Responsive, Error Handling, Font ภาษาไทย |

---

## 📝 หมายเหตุสำคัญ

- ใช้ **uv** เป็น package manager — ไม่ต้องสร้าง venv เอง, ไม่ต้อง activate
- สมาชิกใหม่ทุกคนจะมี `is_approved = FALSE` จนกว่า Admin จะอนุมัติ
- `barcode_uuid` ถูก generate อัตโนมัติด้วย `gen_random_uuid()` (PostgreSQL 13+)
- ใช้ `werkzeug.security` สำหรับ `generate_password_hash` และ `check_password_hash`
- TailwindCSS ใช้ผ่าน CDN ไม่ต้อง build
- HTML5-QRCode CDN: `https://unpkg.com/html5-qrcode`
- Font TH Sarabun New: ดาวน์โหลดไฟล์ `.ttf` วางไว้ที่ `static/fonts/THSarabunNew.ttf` และ register กับ FPDF2:
  ```python
  pdf = FPDF()
  pdf.add_font('THSarabun', '', 'static/fonts/THSarabunNew.ttf', uni=True)
  pdf.set_font('THSarabun', size=12)
  ```
- Barcode format ใช้ **Code128** ซึ่งรองรับ UUID string ได้ครบ
