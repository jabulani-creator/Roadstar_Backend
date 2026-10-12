"""
Write workflows for `scheduler`.

Plain English:
- Staff create pending lesson requests.
- Conflicts are checked against approved bookings only.
- Confirm reserves the slot; cancel keeps history but frees capacity.
- Completing a lesson writes a completion record and deducts credits via commerce.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role, user_is_staff_operator
from catalogue.models import Branch, Course
from commerce.models import EntitlementAccount
from commerce.services import CommerceServiceError, deduct_entitlement
from fleet.models import InstructorProfile, PickupZone, Vehicle, VehicleStatus
from fleet.services import (
    FleetServiceError,
    assert_instructor_eligible,
    assert_pickup_zone_active,
    assert_vehicle_assignable,
    set_vehicle_status,
)
from students.models import Student

from .models import BookingStatus, LessonBooking, LessonCompletion


class SchedulerServiceError(Exception):
    def __init__(self, message: str, code: str = "error", conflicts: list | None = None):
        self.message = message
        self.code = code
        self.conflicts = conflicts or []
        super().__init__(message)


def _can_schedule(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.RECEPTION, StaffRole.INSTRUCTOR],
        )
        or user.is_superuser
        or user.is_staff
    )


def _can_confirm(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(user, [StaffRole.OWNER, StaffRole.RECEPTION])
        or user.is_superuser
        or user.is_staff
    )


def _require_scheduler(actor: User) -> None:
    if not _can_schedule(actor):
        raise SchedulerServiceError("Not allowed to manage schedule.", code="forbidden")


def _require_confirmer(actor: User) -> None:
    if not _can_confirm(actor):
        raise SchedulerServiceError(
            "Not allowed to confirm/reject bookings.",
            code="forbidden",
        )


def _resolve_fk(model, value, *, code: str, label: str):
    if value is None:
        return None
    if isinstance(value, model):
        return value
    obj = model.objects.filter(pk=value).first()
    if obj is None:
        raise SchedulerServiceError(f"{label} not found.", code=code)
    return obj


def _validate_time_range(*, starts_at: datetime, ends_at: datetime, duration_minutes: int) -> None:
    if starts_at >= ends_at:
        raise SchedulerServiceError(
            "Lesson end time must be after start time.",
            code="invalid_time_range",
        )
    if duration_minutes < 1:
        raise SchedulerServiceError(
            "duration_minutes must be at least 1.",
            code="invalid_duration",
        )
    expected = starts_at + timedelta(minutes=duration_minutes)
    # Allow small drift; ends_at should match duration.
    if abs((ends_at - expected).total_seconds()) > 60:
        raise SchedulerServiceError(
            "ends_at must match starts_at + duration_minutes.",
            code="duration_mismatch",
        )


def _effective_window(starts_at, ends_at, travel_buffer_minutes: int):
    buffer = timedelta(minutes=travel_buffer_minutes or 0)
    return starts_at - buffer, ends_at + buffer


def _ranges_overlap(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def find_conflicts(
    *,
    student_id: int,
    instructor_id: int,
    vehicle_id: int,
    starts_at: datetime,
    ends_at: datetime,
    travel_buffer_minutes: int = 0,
    exclude_booking_id: int | None = None,
) -> list[dict]:
    """
    Compare proposed window against approved bookings only.
    Cancelled/rejected/pending/completed do not reserve capacity.
    """
    window_start, window_end = _effective_window(
        starts_at, ends_at, travel_buffer_minutes
    )
    qs = LessonBooking.objects.filter(status=BookingStatus.APPROVED).select_related(
        "student", "instructor", "vehicle"
    )
    if exclude_booking_id:
        qs = qs.exclude(pk=exclude_booking_id)

    conflicts: list[dict] = []
    for booking in qs:
        b_start, b_end = _effective_window(
            booking.starts_at, booking.ends_at, booking.travel_buffer_minutes
        )
        if not _ranges_overlap(window_start, window_end, b_start, b_end):
            continue

        reasons = []
        if booking.student_id == student_id:
            reasons.append("learner")
        if booking.instructor_id == instructor_id:
            reasons.append("instructor")
        if booking.vehicle_id == vehicle_id:
            reasons.append("vehicle")
        if not reasons:
            continue
        conflicts.append(
            {
                "booking_id": booking.id,
                "reasons": reasons,
                "starts_at": booking.starts_at.isoformat(),
                "ends_at": booking.ends_at.isoformat(),
                "student_name": booking.student.full_name,
                "instructor_name": booking.instructor.display_name,
                "vehicle_name": booking.vehicle.name,
            }
        )
    return conflicts


def _validate_resources(
    *,
    instructor: InstructorProfile,
    vehicle: Vehicle,
    course: Course | None,
    pickup_zone: PickupZone | None,
) -> None:
    licence_class = course.licence_class if course else vehicle.licence_class
    transmission = (
        course.transmission
        if course and course.transmission != "both"
        else vehicle.transmission
    )
    # If course is BOTH, match vehicle transmission for instructor check.
    if course and course.transmission == "both":
        transmission = vehicle.transmission

    teach_transmission = "" if transmission == "both" else transmission
    try:
        assert_instructor_eligible(
            instructor,
            licence_class=licence_class or "",
            transmission=teach_transmission,
        )
        assert_vehicle_assignable(vehicle)
        if not vehicle.matches(
            licence_class=licence_class or "",
            transmission=teach_transmission,
        ):
            raise SchedulerServiceError(
                "Vehicle does not match course class/transmission.",
                code="vehicle_mismatch",
            )
        if pickup_zone is not None:
            assert_pickup_zone_active(pickup_zone)
    except FleetServiceError as exc:
        raise SchedulerServiceError(exc.message, code=exc.code) from exc


def _ensure_entitlement(
    *,
    student: Student,
    course: Course | None,
    entitlement_account: EntitlementAccount | None,
) -> EntitlementAccount | None:
    if entitlement_account is not None:
        account = entitlement_account
    elif course is not None:
        account = EntitlementAccount.objects.filter(
            student=student, course=course, is_active=True
        ).first()
    else:
        account = (
            EntitlementAccount.objects.filter(student=student, is_active=True)
            .order_by("-updated_at")
            .first()
        )

    if account is None:
        raise SchedulerServiceError(
            "No entitlement account found for this learner/course.",
            code="entitlement_missing",
        )
    if account.balance_credits < 1:
        raise SchedulerServiceError(
            "Learner has insufficient entitlement credits.",
            code="insufficient_entitlement",
        )
    return account


@transaction.atomic
def create_schedule_request(*, actor: User, data: dict) -> LessonBooking:
    """
    Create a pending request. Conflicts become warnings (non-blocking).
    """
    _require_scheduler(actor)
    payload = dict(data)

    student = _resolve_fk(
        Student, payload.pop("student"), code="student_not_found", label="Student"
    )
    instructor = _resolve_fk(
        InstructorProfile,
        payload.pop("instructor"),
        code="instructor_not_found",
        label="Instructor",
    )
    vehicle = _resolve_fk(
        Vehicle, payload.pop("vehicle"), code="vehicle_not_found", label="Vehicle"
    )
    course = _resolve_fk(
        Course, payload.pop("course", None), code="course_not_found", label="Course"
    )
    branch = _resolve_fk(
        Branch, payload.pop("branch", None), code="branch_not_found", label="Branch"
    )
    pickup_zone = _resolve_fk(
        PickupZone,
        payload.pop("pickup_zone", None),
        code="pickup_zone_not_found",
        label="Pickup zone",
    )
    entitlement = _resolve_fk(
        EntitlementAccount,
        payload.pop("entitlement_account", None),
        code="entitlement_not_found",
        label="Entitlement account",
    )

    starts_at = payload["starts_at"]
    duration_minutes = int(payload.get("duration_minutes") or 0)
    if "ends_at" in payload and payload["ends_at"]:
        ends_at = payload["ends_at"]
        if not duration_minutes:
            duration_minutes = max(
                1, int((ends_at - starts_at).total_seconds() // 60)
            )
    else:
        if duration_minutes < 1:
            # Prefer course lesson unit, else 60 — never hard-code 30 as product truth.
            duration_minutes = (
                course.lesson_unit_minutes
                if course and course.lesson_unit_minutes
                else 60
            )
        ends_at = starts_at + timedelta(minutes=duration_minutes)

    _validate_time_range(
        starts_at=starts_at, ends_at=ends_at, duration_minutes=duration_minutes
    )

    travel_buffer = int(payload.get("travel_buffer_minutes") or 0)
    if pickup_zone and travel_buffer == 0:
        travel_buffer = pickup_zone.travel_buffer_minutes

    _validate_resources(
        instructor=instructor,
        vehicle=vehicle,
        course=course or student.selected_course,
        pickup_zone=pickup_zone,
    )
    account = _ensure_entitlement(
        student=student,
        course=course or student.selected_course,
        entitlement_account=entitlement,
    )

    conflicts = find_conflicts(
        student_id=student.id,
        instructor_id=instructor.id,
        vehicle_id=vehicle.id,
        starts_at=starts_at,
        ends_at=ends_at,
        travel_buffer_minutes=travel_buffer,
    )

    booking = LessonBooking.objects.create(
        student=student,
        course=course or student.selected_course,
        entitlement_account=account,
        instructor=instructor,
        vehicle=vehicle,
        branch=branch or (pickup_zone.branch if pickup_zone else instructor.home_branch),
        pickup_zone=pickup_zone,
        starts_at=starts_at,
        ends_at=ends_at,
        duration_minutes=duration_minutes,
        travel_buffer_minutes=travel_buffer,
        status=BookingStatus.PENDING,
        internal_notes=payload.get("internal_notes") or "",
        conflict_warnings=conflicts,
        created_by=actor,
    )
    return booking


def preview_conflicts(*, actor: User, data: dict) -> list[dict]:
    _require_scheduler(actor)
    student = _resolve_fk(
        Student, data.get("student"), code="student_not_found", label="Student"
    )
    instructor = _resolve_fk(
        InstructorProfile,
        data.get("instructor"),
        code="instructor_not_found",
        label="Instructor",
    )
    vehicle = _resolve_fk(
        Vehicle, data.get("vehicle"), code="vehicle_not_found", label="Vehicle"
    )
    starts_at = data["starts_at"]
    duration_minutes = int(data.get("duration_minutes") or 60)
    ends_at = data.get("ends_at") or (starts_at + timedelta(minutes=duration_minutes))
    travel_buffer = int(data.get("travel_buffer_minutes") or 0)
    return find_conflicts(
        student_id=student.id,
        instructor_id=instructor.id,
        vehicle_id=vehicle.id,
        starts_at=starts_at,
        ends_at=ends_at,
        travel_buffer_minutes=travel_buffer,
        exclude_booking_id=data.get("exclude_booking_id"),
    )


@transaction.atomic
def confirm_booking(
    *,
    actor: User,
    booking: LessonBooking,
    force_override: bool = False,
    override_note: str = "",
) -> LessonBooking:
    _require_confirmer(actor)
    if booking.status not in {
        BookingStatus.PENDING,
        BookingStatus.CHANGE_REQUESTED,
    }:
        raise SchedulerServiceError(
            f"Cannot confirm booking in status {booking.status}.",
            code="invalid_status",
        )

    # Re-validate resources at confirm time.
    _validate_resources(
        instructor=booking.instructor,
        vehicle=booking.vehicle,
        course=booking.course,
        pickup_zone=booking.pickup_zone,
    )
    _ensure_entitlement(
        student=booking.student,
        course=booking.course,
        entitlement_account=booking.entitlement_account,
    )

    conflicts = find_conflicts(
        student_id=booking.student_id,
        instructor_id=booking.instructor_id,
        vehicle_id=booking.vehicle_id,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        travel_buffer_minutes=booking.travel_buffer_minutes,
        exclude_booking_id=booking.id,
    )
    if conflicts and not force_override:
        raise SchedulerServiceError(
            "Conflicts detected. Confirm with force_override and override_note, or reschedule.",
            code="conflicts",
            conflicts=conflicts,
        )
    if conflicts and force_override and not override_note.strip():
        raise SchedulerServiceError(
            "override_note is required when forcing confirmation despite conflicts.",
            code="override_note_required",
            conflicts=conflicts,
        )

    booking.status = BookingStatus.APPROVED
    booking.confirmed_by = actor
    booking.confirmed_at = timezone.now()
    booking.conflict_warnings = conflicts
    if override_note.strip():
        booking.override_note = override_note.strip()
    booking.controller_feedback = ""
    booking.save()
    return booking


@transaction.atomic
def reject_booking(*, actor: User, booking: LessonBooking, feedback: str = "") -> LessonBooking:
    _require_confirmer(actor)
    if booking.status not in {
        BookingStatus.PENDING,
        BookingStatus.CHANGE_REQUESTED,
    }:
        raise SchedulerServiceError(
            f"Cannot reject booking in status {booking.status}.",
            code="invalid_status",
        )
    booking.status = BookingStatus.REJECTED
    booking.controller_feedback = feedback.strip()
    booking.save(update_fields=["status", "controller_feedback", "updated_at"])
    return booking


@transaction.atomic
def request_booking_changes(
    *, actor: User, booking: LessonBooking, feedback: str
) -> LessonBooking:
    _require_confirmer(actor)
    if not feedback.strip():
        raise SchedulerServiceError(
            "Feedback is required when requesting changes.",
            code="feedback_required",
        )
    if booking.status not in {BookingStatus.PENDING, BookingStatus.APPROVED}:
        raise SchedulerServiceError(
            f"Cannot request changes in status {booking.status}.",
            code="invalid_status",
        )
    booking.status = BookingStatus.CHANGE_REQUESTED
    booking.controller_feedback = feedback.strip()
    # Approved bookings that need changes stop blocking until re-confirmed.
    booking.confirmed_at = None
    booking.confirmed_by = None
    booking.save()
    return booking


@transaction.atomic
def cancel_booking(
    *, actor: User, booking: LessonBooking, reason: str = ""
) -> LessonBooking:
    _require_confirmer(actor)
    if booking.status in {
        BookingStatus.CANCELLED,
        BookingStatus.COMPLETED,
        BookingStatus.REJECTED,
    }:
        raise SchedulerServiceError(
            f"Cannot cancel booking in status {booking.status}.",
            code="invalid_status",
        )
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.cancel_reason = reason.strip()
    booking.save(
        update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"]
    )
    return booking


@transaction.atomic
def update_booking(
    *, actor: User, booking: LessonBooking, data: dict
) -> LessonBooking:
    """
    Material changes to an approved booking return it to pending and re-check conflicts.
    """
    _require_scheduler(actor)
    if booking.status in {
        BookingStatus.COMPLETED,
        BookingStatus.CANCELLED,
        BookingStatus.REJECTED,
    }:
        raise SchedulerServiceError(
            f"Cannot update booking in status {booking.status}.",
            code="invalid_status",
        )

    material_fields = {
        "starts_at",
        "ends_at",
        "duration_minutes",
        "instructor",
        "vehicle",
        "pickup_zone",
        "travel_buffer_minutes",
        "student",
        "course",
        "entitlement_account",
        "branch",
    }
    payload = dict(data)
    material_change = any(k in payload for k in material_fields)

    for key in ("student", "instructor", "vehicle", "course", "branch", "pickup_zone", "entitlement_account"):
        if key in payload:
            model = {
                "student": Student,
                "instructor": InstructorProfile,
                "vehicle": Vehicle,
                "course": Course,
                "branch": Branch,
                "pickup_zone": PickupZone,
                "entitlement_account": EntitlementAccount,
            }[key]
            setattr(
                booking,
                key,
                _resolve_fk(
                    model,
                    payload.pop(key),
                    code=f"{key}_not_found",
                    label=key.replace("_", " ").title(),
                ),
            )

    for key in (
        "starts_at",
        "ends_at",
        "duration_minutes",
        "travel_buffer_minutes",
        "internal_notes",
    ):
        if key in payload:
            setattr(booking, key, payload[key])

    if booking.starts_at and booking.duration_minutes and not payload.get("ends_at"):
        booking.ends_at = booking.starts_at + timedelta(minutes=booking.duration_minutes)

    _validate_time_range(
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        duration_minutes=booking.duration_minutes,
    )
    _validate_resources(
        instructor=booking.instructor,
        vehicle=booking.vehicle,
        course=booking.course,
        pickup_zone=booking.pickup_zone,
    )

    conflicts = find_conflicts(
        student_id=booking.student_id,
        instructor_id=booking.instructor_id,
        vehicle_id=booking.vehicle_id,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        travel_buffer_minutes=booking.travel_buffer_minutes,
        exclude_booking_id=booking.id,
    )
    booking.conflict_warnings = conflicts

    if material_change and booking.status == BookingStatus.APPROVED:
        booking.status = BookingStatus.PENDING
        booking.confirmed_at = None
        booking.confirmed_by = None

    booking.save()
    return booking


@transaction.atomic
def complete_lesson(*, actor: User, booking: LessonBooking, data: dict) -> LessonCompletion:
    """
    Write completion + deduct credits (exactly once per booking).
    Vehicle defect flags mark the vehicle unavailable.
    """
    _require_scheduler(actor)
    if booking.status != BookingStatus.APPROVED:
        raise SchedulerServiceError(
            "Only approved bookings can be completed.",
            code="invalid_status",
        )
    if LessonCompletion.objects.filter(booking=booking).exists():
        raise SchedulerServiceError(
            "Lesson already completed.",
            code="already_completed",
        )

    attended = bool(data.get("attended", True))
    no_show = bool(data.get("no_show", False))
    if no_show:
        attended = False

    credits_to_deduct = data.get("credits_to_deduct")
    if credits_to_deduct is None:
        credits_to_deduct = 1 if (attended or no_show) else 0
    credits_to_deduct = int(credits_to_deduct)

    override_note = (data.get("deduction_note") or "").strip()
    if credits_to_deduct == 0 and not override_note:
        raise SchedulerServiceError(
            "deduction_note is required when deducting 0 credits.",
            code="override_note_required",
        )

    completion = LessonCompletion.objects.create(
        booking=booking,
        checked_in_at=data.get("checked_in_at"),
        checked_out_at=data.get("checked_out_at"),
        actual_duration_minutes=data.get("actual_duration_minutes"),
        attended=attended,
        no_show=no_show,
        skills_notes=data.get("skills_notes") or "",
        instructor_notes=data.get("instructor_notes") or "",
        incident_flag=bool(data.get("incident_flag", False)),
        vehicle_defect_flag=bool(data.get("vehicle_defect_flag", False)),
        credits_to_deduct=credits_to_deduct,
        deduction_note=override_note,
        completed_by=actor,
    )

    if credits_to_deduct > 0:
        account = booking.entitlement_account
        if account is None:
            raise SchedulerServiceError(
                "Booking has no entitlement account for deduction.",
                code="entitlement_missing",
            )
        try:
            deduct_entitlement(
                account_id=account.id,
                credits=credits_to_deduct,
                booking_reference=str(booking.id),
                note=override_note or f"Lesson booking #{booking.id}",
                actor=actor,
            )
        except CommerceServiceError as exc:
            raise SchedulerServiceError(exc.message, code=exc.code) from exc
        completion.credits_deducted = True
        completion.save(update_fields=["credits_deducted"])

    if completion.vehicle_defect_flag:
        try:
            set_vehicle_status(
                actor=actor,
                vehicle=booking.vehicle,
                status=VehicleStatus.DEFECT,
                note=override_note
                or f"Defect flagged on lesson booking #{booking.id}",
            )
        except FleetServiceError as exc:
            raise SchedulerServiceError(exc.message, code=exc.code) from exc

    booking.status = BookingStatus.COMPLETED
    booking.save(update_fields=["status", "updated_at"])
    return completion
