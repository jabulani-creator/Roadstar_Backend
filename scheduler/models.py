"""
Durable data for the `scheduler` domain.

Owns: lesson bookings/requests, conflict windows, completion records.

Plain English:
- LessonBooking = a proposed or approved lesson slot.
- Pending requests warn about conflicts but do not reserve capacity.
- Approved bookings block overlapping learner / instructor / vehicle time.
- LessonCompletion = what happened in the lesson + credit deduction link.

Does NOT own: public self-booking marketplace, payments, course catalogue.
"""

from datetime import timedelta

from django.conf import settings
from django.db import models


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending request"
    CHANGE_REQUESTED = "change_requested", "Changes requested"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class LessonBooking(models.Model):
    """
    Staff-managed lesson reservation (request → approved → completed/cancelled).
    """

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="lesson_bookings",
    )
    course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lesson_bookings",
    )
    entitlement_account = models.ForeignKey(
        "commerce.EntitlementAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lesson_bookings",
    )
    instructor = models.ForeignKey(
        "fleet.InstructorProfile",
        on_delete=models.PROTECT,
        related_name="lesson_bookings",
    )
    vehicle = models.ForeignKey(
        "fleet.Vehicle",
        on_delete=models.PROTECT,
        related_name="lesson_bookings",
    )
    branch = models.ForeignKey(
        "catalogue.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lesson_bookings",
    )
    pickup_zone = models.ForeignKey(
        "fleet.PickupZone",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lesson_bookings",
    )

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(
        help_text="Configurable lesson length. Do not assume 30 minutes.",
    )
    travel_buffer_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Extra buffer when pickup applies (or branch turnover).",
    )

    status = models.CharField(
        max_length=32,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )
    internal_notes = models.TextField(blank=True)
    controller_feedback = models.TextField(
        blank=True,
        help_text="Reject / change-request feedback for staff.",
    )
    conflict_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="Non-blocking warnings captured at create/check time.",
    )
    override_note = models.TextField(
        blank=True,
        help_text="Required when confirming despite conflicts (policy override).",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_bookings",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_bookings",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["status", "starts_at"]),
            models.Index(fields=["instructor", "starts_at"]),
            models.Index(fields=["vehicle", "starts_at"]),
            models.Index(fields=["student", "starts_at"]),
        ]

    def __str__(self) -> str:
        return f"Booking #{self.pk} {self.starts_at} ({self.status})"

    @property
    def buffer_start(self):
        return self.starts_at - timedelta(minutes=self.travel_buffer_minutes)

    @property
    def buffer_end(self):
        return self.ends_at + timedelta(minutes=self.travel_buffer_minutes)


class LessonCompletion(models.Model):
    """
    Outcome of a delivered (or no-show) lesson.
    """

    booking = models.OneToOneField(
        LessonBooking,
        on_delete=models.PROTECT,
        related_name="completion",
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    actual_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    attended = models.BooleanField(default=True)
    no_show = models.BooleanField(default=False)
    skills_notes = models.TextField(blank=True)
    instructor_notes = models.TextField(blank=True)
    incident_flag = models.BooleanField(default=False)
    vehicle_defect_flag = models.BooleanField(default=False)
    credits_to_deduct = models.PositiveIntegerField(
        default=1,
        help_text="Credits deducted via commerce (0 allowed with audited override note).",
    )
    credits_deducted = models.BooleanField(default=False)
    deduction_note = models.CharField(max_length=255, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_lessons",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Completion for booking #{self.booking_id}"
