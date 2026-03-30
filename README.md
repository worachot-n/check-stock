# ระบบตรวจสอบคลังอุปกรณ์ (Supply Requisition Inventory System)

ระบบ Web Application สำหรับตรวจสอบและจัดการคลังอุปกรณ์ โดยใช้การสแกน Barcode (UUID) ผ่านกล้องมือถือ

## Tech Stack

| ส่วน | เทคโนโลยี |
|------|-----------|
| Package Manager | [uv](https://docs.astral.sh/uv/) |
| Backend | Python 3.12 + Flask |
| Database | PostgreSQL |
| ORM | Flask-SQLAlchemy |
| Frontend | Jinja2 + TailwindCSS (CDN) |
| Barcode Scanner | HTML5-QRCode (JavaScript) |
| Barcode Generator | python-barcode + Pillow |
| PDF Generator | FPDF2 + Font TH Sarabun New |

---

## การติดตั้ง

### 1. ติดตั้ง uv

```bash
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone และ Install Dependencies

```bash
git clone <repo-url>
cd check-stock
uv sync
```

### 3. ตั้งค่า Environment Variables

คัดลอก `.env` และแก้ไขให้ตรงกับ PostgreSQL ของคุณ:

```env
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/supply_db
DEBUG=true
```

### 4. สร้าง Database

```sql
CREATE DATABASE supply_db;
```

ตาราง `users` และ `supply_requisitions` จะถูกสร้างอัตโนมัติเมื่อรันแอปครั้งแรก

### 5. วาง Font ภาษาไทย

ดาวน์โหลด **TH Sarabun New** (.ttf) และวางไว้ที่:

```
static/fonts/THSarabunNew.ttf
```

> ดาวน์โหลดได้จาก: https://www.f0nt.com/release/th-sarabun-new/

### 6. สร้าง Admin User ครั้งแรก

```bash
uv run python -c "
from app import app
from models import db
from models.user import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        username='admin',
        password_hash=generate_password_hash('your-password'),
        role='admin',
        is_approved=True
    )
    db.session.add(admin)
    db.session.commit()
    print('Admin created.')
"
```

### 7. รันแอป

```bash
# Development
uv run flask --app app run --debug

# เปิดใช้งานบน LAN (มือถือสแกนได้)
uv run flask --app app run --host 0.0.0.0 --port 5000
```

เปิด browser ที่ `http://localhost:5000`

---

## โครงสร้างโปรเจกต์

```
check-stock/
├── pyproject.toml            # uv project config
├── uv.lock                   # uv lockfile
├── .python-version           # Python 3.12
├── .env                      # Environment variables (ไม่ commit)
├── app.py                    # Flask entry point
├── config.py                 # App configuration
├── decorators.py             # @login_required, @admin_required
├── models/
│   ├── __init__.py           # SQLAlchemy instance
│   ├── user.py               # User model
│   └── supply.py             # SupplyRequisition model
├── routes/
│   ├── auth.py               # Login, Register, Reset Password
│   ├── admin.py              # อนุมัติผู้ใช้, จัดการสิทธิ์
│   ├── scanner.py            # Barcode scan API
│   ├── dashboard.py          # ภาพรวมคลังอุปกรณ์
│   └── labels.py             # รายการอุปกรณ์ + PDF Labels
├── templates/
│   ├── base.html
│   ├── auth/                 # login, register, reset_password
│   ├── admin/                # dashboard
│   ├── scanner/              # scan
│   ├── inventory/            # list
│   └── dashboard/            # index
├── static/
│   ├── fonts/
│   │   └── THSarabunNew.ttf  # Font ภาษาไทย
│   └── js/
│       └── scanner.js        # HTML5-QRCode logic
└── utils/
    └── barcode_gen.py        # สร้าง Code128 barcode PNG
```

---

## ฟีเจอร์หลัก

### 🔐 Authentication
- สมัครสมาชิก (รอการอนุมัติจาก Admin)
- เข้าสู่ระบบ / ออกจากระบบ
- รีเซ็ตรหัสผ่าน

### 👤 Admin
- อนุมัติ / ปฏิเสธผู้สมัครใหม่
- เปลี่ยนสิทธิ์ผู้ใช้ (user / admin)

### 📷 Barcode Scanner
- สแกน Barcode ผ่านกล้องมือถือ (Code128 / QR Code)
- ค้นหาด้วย UUID โดยตรง
- ดูและแก้ไขข้อมูลอุปกรณ์
- ยืนยันข้อมูล (verified = true) พร้อมบันทึกผู้ตรวจสอบและเวลา

### 📊 Dashboard
- จำนวนอุปกรณ์ทั้งหมด / ตรวจสอบแล้ว / ยังไม่ตรวจสอบ
- Progress bar ความคืบหน้า
- 10 รายการที่ตรวจสอบล่าสุด

### 🏷️ PDF Label Printing
- รายการอุปกรณ์พร้อม Checkbox
- ค้นหาและ filter รายการ
- เลือกหลายรายการและสร้าง PDF Barcode Labels
- Layout 3 คอลัมน์ต่อหน้า A4
- รองรับ Font ภาษาไทย

---

## API Endpoints

| Method | URL | หน้าที่ |
|--------|-----|--------|
| GET | `/` | Dashboard |
| GET | `/auth/login` | หน้า Login |
| POST | `/auth/login` | เข้าสู่ระบบ |
| GET | `/auth/register` | หน้าสมัครสมาชิก |
| POST | `/auth/register` | สมัครสมาชิก |
| GET | `/auth/logout` | ออกจากระบบ |
| GET | `/auth/reset-password` | หน้ารีเซ็ตรหัสผ่าน |
| POST | `/auth/reset-password` | รีเซ็ตรหัสผ่าน |
| GET | `/admin/users` | จัดการผู้ใช้ (Admin) |
| POST | `/admin/approve/<id>` | อนุมัติผู้ใช้ |
| POST | `/admin/reject/<id>` | ปฏิเสธผู้ใช้ |
| POST | `/admin/set-role/<id>` | เปลี่ยนสิทธิ์ |
| GET | `/scanner` | หน้าสแกน Barcode |
| GET | `/api/get_item/<uuid>` | ดึงข้อมูลอุปกรณ์ (JSON) |
| POST | `/api/verify/<uuid>` | ยืนยันข้อมูล |
| POST | `/api/update/<uuid>` | แก้ไขและบันทึกข้อมูล |
| GET | `/inventory` | รายการอุปกรณ์ทั้งหมด |
| POST | `/labels/generate` | สร้าง PDF Labels |

---

## Database Schema

### `users`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PK | |
| username | VARCHAR(100) UNIQUE | ชื่อผู้ใช้ |
| password_hash | TEXT | รหัสผ่าน (hashed) |
| phone | VARCHAR(20) | เบอร์โทร |
| role | VARCHAR(20) | `user` หรือ `admin` |
| is_approved | BOOLEAN | สถานะการอนุมัติ |
| created_at | TIMESTAMP | วันที่สมัคร |

### `supply_requisitions`
| Column | Type | Description |
|--------|------|-------------|
| sequence_no | SERIAL PK | ลำดับ |
| barcode_uuid | UUID UNIQUE | UUID สำหรับ Barcode |
| item_number | VARCHAR(50) | เลขที่อุปกรณ์ |
| item_name | VARCHAR(255) | ชื่ออุปกรณ์ |
| requisition_item | VARCHAR(255) | รายการขอเบิก |
| issuing_unit | VARCHAR(100) | หน่วยงานที่จ่าย |
| quantity | NUMERIC(10,2) | จำนวน |
| unit_of_measure | VARCHAR(50) | หน่วยนับ |
| verified | BOOLEAN | ผ่านการตรวจสอบแล้ว |
| last_verified_by | INTEGER FK | ผู้ตรวจสอบล่าสุด |
| last_verified_at | TIMESTAMP | เวลาที่ตรวจสอบล่าสุด |
| ... | | และอื่นๆ อีก 10+ fields |

---

## คำสั่ง uv ที่ใช้บ่อย

```bash
uv sync                          # ติดตั้ง dependencies
uv add <package>                 # เพิ่ม package
uv remove <package>              # ลบ package
uv run flask --app app run       # รันแอป
uv run python <script.py>        # รัน Python script
uv lock --upgrade                # อัปเดต dependencies
```
