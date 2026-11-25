# Smart Cafe Reservation System — โครงสร้างโปรเจค Django

โครงสร้างเริ่มต้น (starter scaffold) ของระบบ Smart Cafe Reservation System ตามที่ออกแบบไว้ในเล่มโปรเจค
สร้างด้วย **Django 5 + SQLite (สำหรับ dev) / PostgreSQL (production ตามสไลด์)**

จุดเด่นของโค้ดชุดนี้คือ **ฟีเจอร์ "แก้ไขการจอง" และ "รวมโต๊ะอัตโนมัติตามจำนวนคน"** ที่ implement ครบ พร้อม logic ป้องกันโต๊ะชนกัน (race condition) และผ่านการทดสอบอัตโนมัติแล้ว ตามเอกสาร `tech-design-edit-reservation-table-combine.md` ที่เคยส่งให้ก่อนหน้านี้

---

## 1. วิธีติดตั้งและรัน (บนเครื่องตัวเอง)

```bash
# 1) สร้าง virtual environment (แนะนำ)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2) ติดตั้ง dependencies
pip install -r requirements.txt

# 3) สร้างฐานข้อมูล (ใช้ SQLite เป็นค่าเริ่มต้น ไม่ต้องตั้งค่าอะไรเพิ่ม)
python manage.py migrate

# 4) สร้างบัญชีแอดมิน
python manage.py createsuperuser

# 5) (ทางเลือก แนะนำให้ทำ) สร้างข้อมูลตัวอย่างไว้ทดสอบทันที
python manage.py seed_demo_data

# 6) รันเซิร์ฟเวอร์
python manage.py runserver
```

จากนั้นเปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:8000/`
หน้าหลังบ้าน (Django Admin) อยู่ที่ `http://127.0.0.1:8000/admin/`

### สลับไปใช้ PostgreSQL จริงตามสไลด์

ตั้งค่า environment variables ก่อนรันคำสั่งด้านบน:

```bash
export USE_POSTGRES=True
export POSTGRES_DB=smart_cafe
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=yourpassword
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
pip install psycopg2-binary
```

---

## 2. โครงสร้างโปรเจค (Apps)

| App | หน้าที่ | FR ที่เกี่ยวข้อง |
|---|---|---|
| `accounts` | สมัครสมาชิก / เข้า-ออกระบบ (Custom User model แยก role: customer/staff/admin) | FR-01 ถึง FR-03 |
| `tables` | จัดการโต๊ะ, ผังร้าน, ชุดโต๊ะรวม (TableGroup) | FR-04, FR-05, FR-23, FR-34 |
| `reservations` | **หัวใจของระบบ**: จองโต๊ะ, แก้ไขการจอง, ยกเลิก, อัลกอริทึมแนะนำ/รวมโต๊ะ | FR-06 ถึง FR-09, FR-24, FR-28 ถึง FR-33 |
| `menus` | เมนูอาหาร/เครื่องดื่ม | FR-10, FR-25 |
| `orders` | สั่งซื้อสินค้า, ตะกร้า, สถานะออเดอร์ | FR-11 ถึง FR-14, FR-19, FR-20 |
| `promotions` | โปรโมชั่น | FR-26 |
| `ai_assistant` | โครง RAG pipeline (Retrieval พร้อมใช้ ยังไม่เชื่อม LLM จริง) | FR-15 ถึง FR-17, FR-27 |

### จุดที่ควรอ่านก่อนเพื่อนต่อยอด

- **`reservations/models.py`** — ดู `Reservation`, `ReservationTable` (ตารางกลาง many-to-many), `ReservationHistory`
- **`reservations/services.py`** — Logic ทั้งหมด: `find_table_for_party()` (อัลกอริทึมแนะนำ/รวมโต๊ะ), `confirm_reservation()`, `edit_reservation()`, `cancel_reservation()` — มีคอมเมนต์อธิบายเหตุผลของทุก edge case
- **`tables/models.py`** — `TableGroup` / `TableGroupMember` คือกลไกให้แอดมินกำหนดว่าโต๊ะไหนรวมกับโต๊ะไหนได้จริงในทางกายภาพ (ตั้งค่าได้ที่ Django Admin)

---

## 3. ฟีเจอร์ที่ implement ไว้แล้ว (ใช้งานได้จริงผ่านหน้าเว็บ)

- สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ
- ดูผังร้าน (ลูกค้าเห็นแค่ ว่าง/ไม่ว่าง, staff/admin เห็นสถานะเต็ม)
- จองโต๊ะโดยระบุจำนวนคน → ระบบแนะนำโต๊ะเดี่ยวที่พอดีที่สุด หรือรวมโต๊ะอัตโนมัติถ้าจำเป็น
- แก้ไขการจอง (เปลี่ยนวัน/เวลา/จำนวนคน) โดยไม่ต้องยกเลิกแล้วจองใหม่ พร้อมจำกัดจำนวนครั้งที่แก้ไขได้
- ยกเลิกการจอง (ปล่อยคืนโต๊ะทุกตัวในชุดอัตโนมัติ)
- ดูเมนู / สั่งเมนูผูกกับการจอง / ดูสถานะออเดอร์
- ดูโปรโมชั่น
- หน้า Django Admin จัดการโต๊ะ, ชุดโต๊ะรวม, เมนู, โปรโมชั่น, ดูประวัติการแก้ไขการจอง (ReservationHistory)
- หน้า AI Chatbot เบื้องต้น (ตอบจาก keyword search ใน Knowledge Base จริง แต่ยังไม่ได้เชื่อม LLM)

## 4. สิ่งที่ยังต้องทำต่อ (ไม่ได้อยู่ใน scope ของโค้ดชุดนี้)

1. **เชื่อม LLM จริงเข้ากับ `ai_assistant/services.py`** (เช่น OpenAI API หรือ Gemini API) แทนคำตอบ stub ปัจจุบัน — ดู `generate_answer()` มีคอมเมนต์บอกจุดที่ต้องแก้ไว้แล้ว
2. **หน้าจอผังร้านแบบกราฟิก/ลากวาง** สำหรับแอดมิน (ตอนนี้เป็น grid ธรรมดา ยังไม่ได้ใช้พิกัด pos_x/pos_y ที่เตรียมไว้ในโมเดล)
3. **ระบบแจ้งเตือน Email/LINE Notify** จริง (ตอนนี้มีแค่ `messages` framework แสดงผลในเว็บ)
4. **ทดสอบ concurrency จริงจัง** ระดับ production (โค้ดใช้ `select_for_update()` ป้องกันโต๊ะชนกันแล้ว แต่ควรทำ load test เพิ่มก่อนใช้งานจริง)
5. Login ผ่าน Google OAuth (ตอนนี้เป็น username/password ธรรมดา)

## 5. การทดสอบ

โค้ด logic หลัก (`reservations/services.py`) ผ่านการทดสอบอัตโนมัติแบบ end-to-end แล้ว ครอบคลุม:
- แนะนำโต๊ะเดี่ยวถูกต้องตามความจุที่พอดีที่สุด
- แนะนำรวมโต๊ะเมื่อไม่มีโต๊ะเดี่ยวพอ
- แก้ไขการจองโดยไม่จำเป็นต้องย้ายโต๊ะถ้าโต๊ะเดิมยังพอ (regression test ที่จับบั๊กจริงเจอระหว่างพัฒนา — ดูรายละเอียดในคอมเมนต์โค้ด `edit_reservation()`)
- แก้ไขจนต้องย้ายโต๊ะและปล่อยคืนโต๊ะเดิมถูกต้อง
- จำกัดจำนวนครั้งการแก้ไข
- ป้องกันการจองโต๊ะซ้ำเมื่อโต๊ะเต็มร้าน

แนะนำให้เขียนเป็น Django TestCase อย่างเป็นทางการ (`reservations/tests.py`) ก่อนส่งอาจารย์ เพื่อให้รันซ้ำได้และโชว์ในการนำเสนอได้ว่ามี unit test จริง
