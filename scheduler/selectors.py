"""Read queries for scheduler — staff calendar, instructor day, student upcoming."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from students.models import Student

from .models import BookingStatus, LessonBooking


def bookings_staff(
    *,
    status: str | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    instructor_id: int | None = None,
    student_id: int | None = None,
) -> QuerySet[LessonBooking]:
    qs = LessonBooking.objects.select_related(
        "student",
        "course",
        "entitlement_account",
        "instructor",
        "vehicle",
        "branch",
        "pickup_zone",
        "created_by",
        "confirmed_by",
    ).prefetch_related("completion")
    if status:
        qs = qs.filter(status=status)
    if from_dt:
        qs = qs.filter(ends_at__gte=from_dt)
    if to_dt:
        qs = qs.filter(starts_at__lte=to_dt)
    if instructor_id is not None:
        qs = qs.filter(instructor_id=instructor_id)
    if student_id is not None:
        qs = qs.filter(student_id=student_id)
    return qs.order_by("starts_at")


def booking_by_id(*, booking_id: int) -> LessonBooking | None:
    return (
        LessonBooking.objects.select_related(
            "student",
            "course",
            "entitlement_account",
            "instructor",
            "vehicle",
            "branch",
            "pickup_zone",
        )
        .prefetch_related("completion")
        .filter(pk=booking_id)
        .first()
    )


def upcoming_for_student(*, student: Student) -> QuerySet[LessonBooking]:
    now = timezone.now()
    return bookings_staff(student_id=student.id).filter(
        status=BookingStatus.APPROVED,
        ends_at__gte=now,
    )


def instructor_daily_view(
    *, instructor_id: int, day: date | None = None
) -> QuerySet[LessonBooking]:
    day = day or timezone.localdate()
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    return bookings_staff(instructor_id=instructor_id).filter(
        status__in=[BookingStatus.APPROVED, BookingStatus.COMPLETED],
        starts_at__gte=start,
        starts_at__lt=end,
    )
