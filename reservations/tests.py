"""
Unit tests สำหรับ logic การจอง/แก้ไขการจอง/รวมโต๊ะอัตโนมัติ + หน้าจองแบบใหม่ (เลือกวันที่ -> ผังร้าน)
รันด้วยคำสั่ง: python manage.py test reservations
"""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from tables.models import Table, TableGroup, TableGroupMember

from .models import Reservation
from .services import (
    ReservationError,
    cancel_reservation,
    confirm_reservation,
    edit_reservation,
    find_table_for_party,
)

# ใช้วันที่แบบสัมพัทธ์กับ "วันนี้" (ไม่ใช่วันที่ hardcode) เพื่อไม่ให้เทสต์พังเมื่อเวลาผ่านไป
# เนื่องจาก find_table_for_party/confirm_reservation/edit_reservation ห้ามจองวันที่ย้อนหลัง
# และห้ามจองข้ามเดือนปัจจุบัน (_validate_booking_window) จึงต้องอยู่ภายในเดือนเดียวกับวันนี้
_today = date.today()
_last_day_of_month = (
    date(_today.year + (_today.month // 12), (_today.month % 12) + 1, 1)
    - timedelta(days=1)
).day
_BASE_DAY = min(_today.day + 1, _last_day_of_month - 3)
DAY_0 = _today.replace(day=_BASE_DAY)
DAY_1 = _today.replace(day=_BASE_DAY + 1)
DAY_2 = _today.replace(day=_BASE_DAY + 2)
DAY_3 = _today.replace(day=_BASE_DAY + 3)


class TableRecommendationTests(TestCase):
    """FR-28, FR-29, FR-30: ระบุจำนวนคน + แนะนำโต๊ะเดี่ยว/รวมโต๊ะอัตโนมัติ (ใช้ตอนแก้ไขการจอง)"""

    def setUp(self):
        self.t1 = Table.objects.create(table_number=1, zone="A", capacity=2)
        self.t4 = Table.objects.create(table_number=4, zone="B", capacity=4)
        self.t11 = Table.objects.create(table_number=11, zone="B", capacity=4)
        self.t20 = Table.objects.create(table_number=20, zone="C", capacity=6)

        self.group = TableGroup.objects.create(group_name="ชุดรวม 4+11")
        TableGroupMember.objects.create(group=self.group, table=self.t4)
        TableGroupMember.objects.create(group=self.group, table=self.t11)

        self.user = User.objects.create_user(username="customer1", password="pass12345")

    def test_recommends_smallest_fitting_single_table(self):
        suggestion = find_table_for_party(DAY_0, 2)
        self.assertEqual(suggestion.suggestion_type, "single")
        self.assertEqual(suggestion.tables[0].table_number, 1)

    def test_recommends_best_fit_not_oversized_table(self):
        # party_size=5 ควรได้โต๊ะ 20 (คนพอดีสุดในบรรดาโต๊ะเดี่ยวที่จุพอ) ไม่ใช่โต๊ะรวม
        suggestion = find_table_for_party(DAY_0, 5)
        self.assertEqual(suggestion.suggestion_type, "single")
        self.assertEqual(suggestion.tables[0].table_number, 20)

    def test_falls_back_to_combined_tables_when_no_single_table_fits(self):
        suggestion = find_table_for_party(DAY_0, 7)
        self.assertEqual(suggestion.suggestion_type, "combined")
        self.assertEqual(
            sorted(t.table_number for t in suggestion.tables), [4, 11]
        )

    def test_returns_none_when_nothing_fits(self):
        suggestion = find_table_for_party(DAY_0, 999)
        self.assertEqual(suggestion.suggestion_type, "none")

    def test_combined_group_not_suggested_if_one_member_is_busy(self):
        # จองโต๊ะ 11 ไปก่อน -> ชุดรวม 4+11 ต้องใช้ไม่ได้แล้ว
        confirm_reservation(self.user, DAY_0, 4, [self.t11])
        suggestion = find_table_for_party(DAY_0, 7)
        self.assertEqual(suggestion.suggestion_type, "none")


class ReservationConfirmationTests(TestCase):
    def setUp(self):
        self.t4 = Table.objects.create(table_number=4, zone="B", capacity=4)
        self.t11 = Table.objects.create(table_number=11, zone="B", capacity=4)
        self.user = User.objects.create_user(username="customer1", password="pass12345")

    def test_confirm_reservation_marks_all_tables_reserved(self):
        reservation = confirm_reservation(self.user, DAY_0, 7, [self.t4, self.t11])
        self.t4.refresh_from_db()
        self.t11.refresh_from_db()
        self.assertEqual(self.t4.status, Table.Status.RESERVED)
        self.assertEqual(self.t11.status, Table.Status.RESERVED)
        self.assertTrue(reservation.is_combined())

    def test_confirm_reservation_raises_if_table_already_reserved(self):
        confirm_reservation(self.user, DAY_0, 4, [self.t4])
        with self.assertRaises(ReservationError):
            confirm_reservation(self.user, DAY_0, 4, [self.t4])

    def test_confirm_reservation_requires_at_least_one_table(self):
        with self.assertRaises(ReservationError):
            confirm_reservation(self.user, DAY_0, 2, [])

    def test_confirm_reservation_rejects_insufficient_capacity(self):
        # t4 จุได้ 4 คน แต่จองสำหรับ 10 คน -> ต้องไม่ผ่าน (ไม่พอ)
        with self.assertRaises(ReservationError):
            confirm_reservation(self.user, DAY_0, 10, [self.t4])

    def test_confirm_reservation_rejects_past_date(self):
        yesterday = _today - timedelta(days=1)
        with self.assertRaises(ReservationError):
            confirm_reservation(self.user, yesterday, 2, [self.t4])


class ReservationEditTests(TestCase):
    """FR-32, FR-33: แก้ไขการจอง"""

    def setUp(self):
        self.t1 = Table.objects.create(table_number=1, zone="A", capacity=2)
        self.t4 = Table.objects.create(table_number=4, zone="B", capacity=4)
        self.t11 = Table.objects.create(table_number=11, zone="B", capacity=4)
        self.group = TableGroup.objects.create(group_name="ชุดรวม 4+11")
        TableGroupMember.objects.create(group=self.group, table=self.t4)
        TableGroupMember.objects.create(group=self.group, table=self.t11)
        self.user = User.objects.create_user(username="customer1", password="pass12345")
        self.reservation = confirm_reservation(self.user, DAY_0, 7, [self.t4, self.t11])

    def test_edit_keeps_same_tables_when_they_still_fit(self):
        """
        Regression test: บั๊กที่เคยเจอระหว่างพัฒนาคือระบบมองว่าโต๊ะที่การจองนี้ถืออยู่แล้ว
        'ไม่ว่าง' (เพราะยังไม่ได้ปล่อยสถานะก่อนค้นหา) ทำให้ย้ายไปโต๊ะอื่นทั้งที่ไม่จำเป็น
        """
        edit_reservation(self.reservation, new_date=DAY_1, new_party_size=7)
        self.reservation.refresh_from_db()
        table_numbers = sorted(t.table_number for t in self.reservation.tables.all())
        self.assertEqual(table_numbers, [4, 11])

    def test_edit_moves_to_smaller_table_and_releases_old_ones(self):
        edit_reservation(self.reservation, new_date=DAY_1, new_party_size=2)
        self.t1.refresh_from_db()
        self.t4.refresh_from_db()
        self.t11.refresh_from_db()
        self.assertEqual(self.t1.status, Table.Status.RESERVED)
        self.assertEqual(self.t4.status, Table.Status.AVAILABLE)
        self.assertEqual(self.t11.status, Table.Status.AVAILABLE)

    def test_edit_fails_when_no_table_fits_new_party_size(self):
        with self.assertRaises(ReservationError):
            edit_reservation(self.reservation, new_date=DAY_1, new_party_size=999)

    def test_edit_respects_max_edit_count(self):
        edit_reservation(self.reservation, new_date=DAY_1, new_party_size=2)
        edit_reservation(self.reservation, new_date=DAY_2, new_party_size=2)
        with self.assertRaises(ReservationError):
            edit_reservation(self.reservation, new_date=DAY_3, new_party_size=2)

    def test_cannot_edit_after_checked_in(self):
        self.reservation.status = "preparing"
        self.reservation.save()
        with self.assertRaises(ReservationError):
            edit_reservation(self.reservation, new_date=DAY_1, new_party_size=2)


class ReservationCancelTests(TestCase):
    def setUp(self):
        self.t4 = Table.objects.create(table_number=4, zone="B", capacity=4)
        self.t11 = Table.objects.create(table_number=11, zone="B", capacity=4)
        self.user = User.objects.create_user(username="customer1", password="pass12345")
        self.reservation = confirm_reservation(self.user, DAY_0, 7, [self.t4, self.t11])

    def test_cancel_releases_all_tables_in_the_group(self):
        cancel_reservation(self.reservation)
        self.t4.refresh_from_db()
        self.t11.refresh_from_db()
        self.assertEqual(self.t4.status, Table.Status.AVAILABLE)
        self.assertEqual(self.t11.status, Table.Status.AVAILABLE)

    def test_cannot_cancel_twice(self):
        cancel_reservation(self.reservation)
        with self.assertRaises(ReservationError):
            cancel_reservation(self.reservation)


class ReservationDateStepViewTests(TestCase):
    """หน้าขั้นที่ 1 ของการจองใหม่: เลือกวันที่จากปฏิทิน"""

    def setUp(self):
        self.user = User.objects.create_user(username="customer1", password="pass12345")
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("reservations:create"))
        self.assertNotEqual(resp.status_code, 200)

    def test_shows_calendar_with_todays_date_bookable(self):
        resp = self.client.get(reverse("reservations:create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, str(_today.day))


class ReservationFloorPlanBookingViewTests(TestCase):
    """หน้าขั้นที่ 2 ของการจองใหม่: เลือกโต๊ะจากผังร้านของวันที่เลือกไว้"""

    def setUp(self):
        self.user = User.objects.create_user(username="customer1", password="pass12345")
        self.client.force_login(self.user)
        self.t1 = Table.objects.create(table_number=1, zone="A", capacity=2, pos_x=10, pos_y=10)
        self.t4 = Table.objects.create(table_number=4, zone="B", capacity=4, pos_x=30, pos_y=10)

    def _url(self, d):
        return reverse("reservations:create_floorplan", kwargs={"date_str": d.isoformat()})

    def test_already_reserved_table_shown_as_busy_and_not_selectable(self):
        confirm_reservation(self.user, DAY_0, 2, [self.t1])
        resp = self.client.get(self._url(DAY_0))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ไม่ว่าง")

    def test_booking_a_single_available_table_succeeds(self):
        resp = self.client.post(
            self._url(DAY_0), {"table_ids": [self.t1.id], "party_size": 2}
        )
        self.assertRedirects(resp, reverse("reservations:my_reservations"))
        self.assertEqual(Reservation.objects.filter(customer=self.user).count(), 1)

    def test_booking_combined_tables_succeeds(self):
        resp = self.client.post(
            self._url(DAY_0),
            {"table_ids": [self.t1.id, self.t4.id], "party_size": 6},
        )
        self.assertRedirects(resp, reverse("reservations:my_reservations"))
        reservation = Reservation.objects.get(customer=self.user)
        self.assertTrue(reservation.is_combined())

    def test_rejects_date_outside_current_month(self):
        next_month = (DAY_0.replace(day=28) + timedelta(days=10))
        resp = self.client.post(
            self._url(next_month), {"table_ids": [self.t1.id], "party_size": 2}
        )
        self.assertRedirects(resp, reverse("reservations:create"))
        self.assertEqual(Reservation.objects.count(), 0)
