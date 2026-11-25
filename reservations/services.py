"""
Business logic ของการจองโต๊ะ แยกออกจาก views ตามหลัก "fat model / thin view"
ตรงกับอัลกอริทึมที่ออกแบบไว้ในเอกสาร tech-design-edit-reservation-table-combine.md
"""

from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from tables.models import Table, TableGroup

from .models import Reservation, ReservationHistory, ReservationTable


class ReservationError(Exception):
    """ข้อผิดพลาดทางธุรกิจของการจอง (ใช้แสดงข้อความให้ผู้ใช้เห็นตรง ๆ ได้)"""


@dataclass
class TableSuggestion:
    suggestion_type: str  # "single" | "combined" | "none"
    tables: list = field(default_factory=list)

    @property
    def total_capacity(self):
        return sum(t.capacity for t in self.tables)


def _tables_with_conflicting_reservation(reservation_date, exclude_reservation_id=None):
    """คืนค่า id ของโต๊ะที่ถูกจองไปแล้วในวันนั้น (สถานะยังไม่ถูกยกเลิก) - จองเป็นรายวัน ไม่แยกตามเวลา"""
    qs = ReservationTable.objects.filter(
        reservation__reservation_date=reservation_date,
    ).exclude(reservation__status=Reservation.Status.CANCELLED)

    if exclude_reservation_id:
        qs = qs.exclude(reservation_id=exclude_reservation_id)

    return set(qs.values_list("table_id", flat=True))


def table_availability_for_date(reservation_date, exclude_reservation_id=None):
    """
    คืนค่า set ของ table id ที่ "ไม่ว่าง" สำหรับวันที่ที่ระบุ ใช้แสดงผังโต๊ะตอนลูกค้าจอง
    (หน้า "เลือกโต๊ะจากผังร้าน" - FR-06): ไม่ว่าง = สถานะโต๊ะไม่ใช่ available อยู่แล้ว
    หรือมีคนจองไปแล้วในวันนั้น
    """
    busy_ids = _tables_with_conflicting_reservation(reservation_date, exclude_reservation_id)
    not_available_status_ids = set(
        Table.objects.exclude(status=Table.Status.AVAILABLE).values_list("id", flat=True)
    )
    return busy_ids | not_available_status_ids


def find_table_for_party(reservation_date, party_size, exclude_reservation_id=None):
    """
    อัลกอริทึมแนะนำโต๊ะตามจำนวนคน (FR-29, FR-30) - ใช้ตอนแก้ไขการจอง (edit_reservation)
    เพื่อหาโต๊ะใหม่ให้อัตโนมัติเมื่อจำนวนคน/วันที่เปลี่ยนจนโต๊ะเดิมไม่พอ/ไม่ว่างแล้ว:
    1. หาโต๊ะเดี่ยวที่จุพอดีที่สุดก่อน (เสียพื้นที่ว่างน้อยที่สุด)
    2. ถ้าไม่มีโต๊ะเดี่ยวพอ ให้หาชุดโต๊ะรวม (TableGroup) ที่ทุกโต๊ะว่างพร้อมกัน
    3. ถ้าไม่พบทั้งคู่ คืนค่า suggestion_type = "none"
    """

    busy_table_ids = _tables_with_conflicting_reservation(
        reservation_date, exclude_reservation_id
    )

    available_tables = Table.objects.filter(status=Table.Status.AVAILABLE).exclude(
        id__in=busy_table_ids
    )

    # 1) ลองหาโต๊ะเดี่ยวที่จุพอดีที่สุด
    single_candidates = sorted(
        [t for t in available_tables if t.capacity >= party_size],
        key=lambda t: t.capacity - party_size,
    )
    if single_candidates:
        return TableSuggestion(suggestion_type="single", tables=[single_candidates[0]])

    # 2) ลองหาชุดโต๊ะรวม
    available_ids = set(available_tables.values_list("id", flat=True))
    best_group = None
    for group in TableGroup.objects.prefetch_related("tables"):
        member_ids = set(group.tables.values_list("id", flat=True))
        if not member_ids.issubset(available_ids):
            continue  # มีบางโต๊ะในชุดไม่ว่าง ข้ามไป
        total_capacity = sum(t.capacity for t in group.tables.all())
        if total_capacity >= party_size:
            if best_group is None or total_capacity < best_group[0]:
                best_group = (total_capacity, list(group.tables.all()))

    if best_group:
        return TableSuggestion(suggestion_type="combined", tables=best_group[1])

    return TableSuggestion(suggestion_type="none", tables=[])


@transaction.atomic
def confirm_reservation(user, reservation_date, party_size, tables):
    """
    ยืนยันการจอง (รองรับทั้งโต๊ะเดี่ยวและโต๊ะรวมที่ลูกค้าเลือกเองจากผังร้าน - FR-06)
    พร้อมล็อกกันโต๊ะชนกัน (race condition)
    """
    if not tables:
        raise ReservationError("กรุณาเลือกโต๊ะอย่างน้อย 1 โต๊ะ")

    _validate_booking_window(reservation_date)

    if sum(t.capacity for t in tables) < party_size:
        raise ReservationError("โต๊ะที่เลือกจุคนได้ไม่พอ กรุณาเลือกโต๊ะเพิ่ม หรือเลือกโต๊ะอื่น")

    table_ids = [t.id for t in tables]
    locked_tables = list(Table.objects.select_for_update().filter(id__in=table_ids))

    busy_table_ids = _tables_with_conflicting_reservation(reservation_date)
    for t in locked_tables:
        if t.status != Table.Status.AVAILABLE or t.id in busy_table_ids:
            raise ReservationError(
                f"โต๊ะ {t.table_number} เพิ่งถูกจองไปแล้ว กรุณาเลือกโต๊ะอื่น หรือลองวันอื่น"
            )

    reservation = Reservation.objects.create(
        customer=user,
        party_size=party_size,
        reservation_date=reservation_date,
        status=Reservation.Status.RESERVED,
    )

    for t in locked_tables:
        ReservationTable.objects.create(reservation=reservation, table=t)
        t.status = Table.Status.RESERVED
        t.save(update_fields=["status"])

    return reservation


def _validate_booking_window(reservation_date):
    """
    Business rule เดิม: จองล่วงหน้าได้ 1 วัน ก่อนเวลา 24.00 น. และต้องอยู่ภายในเดือนปัจจุบันเท่านั้น
    """
    today = timezone.localdate()
    if reservation_date < today:
        raise ReservationError("ไม่สามารถจองวันที่ผ่านมาแล้วได้")
    if reservation_date.month != today.month or reservation_date.year != today.year:
        raise ReservationError("สามารถจองได้เฉพาะวันที่อยู่ภายในเดือนปัจจุบันเท่านั้น")


@transaction.atomic
def edit_reservation(reservation, new_date, new_party_size):
    """
    แก้ไขการจอง (FR-32, FR-33) โดยไม่ต้องยกเลิกแล้วจองใหม่
    """
    if not reservation.is_editable():
        raise ReservationError(
            "ไม่สามารถแก้ไขการจองนี้ได้ เนื่องจากลูกค้าเช็คอิน/เริ่มใช้บริการแล้ว กรุณาติดต่อพนักงานหน้าร้าน"
        )

    max_edits = getattr(settings, "RESERVATION_MAX_EDIT_COUNT", 2)
    if reservation.edit_count >= max_edits:
        raise ReservationError(f"การจองนี้ถูกแก้ไขครบ {max_edits} ครั้งแล้ว ไม่สามารถแก้ไขเพิ่มได้")

    _validate_booking_window(new_date)

    old_tables = list(reservation.tables.select_for_update())
    needs_new_tables = (
        new_party_size != reservation.party_size
        or new_date != reservation.reservation_date
    )

    if needs_new_tables:
        # สำคัญ: ต้อง "ปล่อยคืน" โต๊ะเดิมก่อนค้นหา ไม่เช่นนั้นโต๊ะที่การจองนี้ถืออยู่แล้ว
        # จะโดนมองว่า "ไม่ว่าง" ไปด้วย (เพราะ Table.status ยังเป็น reserved อยู่)
        # ทำให้แม้โต๊ะเดิมยังพอสำหรับจำนวนคน/เวลาใหม่ ระบบก็จะพยายามหาโต๊ะอื่นแทนโดยไม่จำเป็น
        # ถ้าหาโต๊ะใหม่ไม่ได้ ฟังก์ชันนี้จะ raise แล้วทั้งหมดจะถูก rollback อัตโนมัติ (เพราะอยู่ใน @transaction.atomic)
        for t in old_tables:
            t.status = Table.Status.AVAILABLE
            t.save(update_fields=["status"])
        ReservationTable.objects.filter(reservation=reservation).delete()

        suggestion = find_table_for_party(
            new_date, new_party_size, exclude_reservation_id=reservation.id
        )
        if suggestion.suggestion_type == "none":
            raise ReservationError("ไม่มีโต๊ะว่างเพียงพอสำหรับวัน/จำนวนคนใหม่ที่ต้องการ")
        new_tables = suggestion.tables

        for t in new_tables:
            ReservationTable.objects.create(reservation=reservation, table=t)
            t.status = Table.Status.RESERVED
            t.save(update_fields=["status"])
    else:
        # ไม่มีอะไรกระทบโต๊ะ (วัน/เวลา/จำนวนคนเดิมทั้งหมด) -> ไม่ต้องแตะสถานะโต๊ะเลย
        new_tables = old_tables

    def _log(field_name, old_value, new_value):
        if str(old_value) != str(new_value):
            ReservationHistory.objects.create(
                reservation=reservation,
                field_changed=field_name,
                old_value=str(old_value),
                new_value=str(new_value),
            )

    _log("reservation_date", reservation.reservation_date, new_date)
    _log("party_size", reservation.party_size, new_party_size)
    _log(
        "tables",
        ",".join(str(t.table_number) for t in old_tables),
        ",".join(str(t.table_number) for t in new_tables),
    )

    reservation.reservation_date = new_date
    reservation.party_size = new_party_size
    reservation.edit_count += 1
    reservation.save()

    return reservation


@transaction.atomic
def seat_walkin(table, guest_name, party_size):
    """
    รับลูกค้าวอล์กอิน (ไม่มีบัญชีสมาชิก/ไม่ได้จองล่วงหน้า): พนักงานเลือกโต๊ะที่ว่าง
    กรอกชื่อลูกค้าและจำนวนคน ระบบจะสร้างการจองของวันนี้ให้ทันที (สถานะ "กำลังเตรียม/รอออเดอร์"
    เพราะลูกค้านั่งที่โต๊ะแล้ว ไม่ใช่แค่จองล่วงหน้า) แล้วเปลี่ยนสถานะโต๊ะให้ตรงกัน
    """
    guest_name = (guest_name or "").strip()
    if not guest_name:
        raise ReservationError("กรุณาระบุชื่อลูกค้า")
    if party_size < 1:
        raise ReservationError("กรุณาระบุจำนวนคน")

    locked_table = Table.objects.select_for_update().filter(id=table.id).first()
    if locked_table is None:
        raise ReservationError("ไม่พบโต๊ะที่เลือก")

    today = timezone.localdate()
    busy_table_ids = _tables_with_conflicting_reservation(today)
    if locked_table.status != Table.Status.AVAILABLE or locked_table.id in busy_table_ids:
        raise ReservationError(f"โต๊ะ {locked_table.table_number} ไม่ว่างแล้ว กรุณาเลือกโต๊ะอื่น")

    reservation = Reservation.objects.create(
        customer=None,
        guest_name=guest_name,
        is_walkin=True,
        party_size=party_size,
        reservation_date=today,
        status=Reservation.Status.PREPARING,
    )
    ReservationTable.objects.create(reservation=reservation, table=locked_table)
    locked_table.status = Table.Status.PREPARING
    locked_table.save(update_fields=["status"])

    return reservation


@transaction.atomic
def cancel_reservation(reservation):
    """FR-07: ยกเลิกการจอง -> ปล่อยคืนโต๊ะทุกตัวในชุดกลับเป็น Available"""
    if reservation.status == Reservation.Status.CANCELLED:
        raise ReservationError("การจองนี้ถูกยกเลิกไปแล้ว")

    for t in reservation.tables.select_for_update():
        t.status = Table.Status.AVAILABLE
        t.save(update_fields=["status"])

    reservation.status = Reservation.Status.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])
    return reservation
