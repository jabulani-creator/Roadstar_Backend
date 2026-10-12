"""
Durable data for the `students` domain.

Owns: learner profiles, registration checklist, consents, sponsor fields.

Plain English:
- Student = a registered learner (not just a WhatsApp enquiry).
- Linked User account = how they log into the portal.
- Consent records = proof they accepted terms (required to register).
- Checklist = which enrolment documents staff have collected.

Does NOT own: payments, lesson credits, course prices, bookings.
"""

from django.conf import settings
from django.db import models


class StudentStatus(models.TextChoices):
    REGISTERED = "registered", "Registered (awaiting payment / start)"
    ACTIVE = "active", "Active learner"
    COMPLETED = "completed", "Completed / graduated"
    WITHDRAWN = "withdrawn", "Withdrawn"
    INACTIVE = "inactive", "Inactive"


class DocumentChecklistStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    PARTIAL = "partial", "Partial"
    COMPLETE = "complete", "Complete"
    WAIVED = "waived", "Waived by staff"


class ConsentType(models.TextChoices):
    TERMS = "terms", "Terms of training"
    PRIVACY = "privacy", "Privacy / data processing"
    MARKETING = "marketing", "Marketing updates (optional)"


class Student(models.Model):
    """
    Registered learner profile.

    One student ↔ one portal user account (when an account exists).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profile",
    )

    # Identity
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=32)
    email = models.EmailField()
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="NRC / national ID reference. Staff/student only — never public.",
    )

    # Training pathway
    selected_course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="students",
    )
    preferred_branch = models.ForeignKey(
        "catalogue.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="students",
    )
    preferred_schedule = models.CharField(max_length=255, blank=True)
    pickup_notes = models.TextField(
        blank=True,
        help_text="Pickup address/notes for staff. Not public.",
    )

    # Optional sponsor / payer
    sponsor_name = models.CharField(max_length=160, blank=True)
    sponsor_phone = models.CharField(max_length=32, blank=True)
    sponsor_email = models.EmailField(blank=True)
    sponsor_relationship = models.CharField(max_length=80, blank=True)

    # Capture metadata
    referral_source = models.CharField(max_length=32, blank=True)
    referral_detail = models.CharField(max_length=255, blank=True)
    source_lead = models.ForeignKey(
        "leads.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resulting_students",
    )

    # Enrolment ops
    status = models.CharField(
        max_length=32,
        choices=StudentStatus.choices,
        default=StudentStatus.REGISTERED,
    )
    checklist_status = models.CharField(
        max_length=32,
        choices=DocumentChecklistStatus.choices,
        default=DocumentChecklistStatus.NOT_STARTED,
    )
    has_nrc_copy = models.BooleanField(default=False)
    has_medical_form = models.BooleanField(default=False)
    has_photos = models.BooleanField(default=False)
    has_proof_of_payment = models.BooleanField(default=False)
    internal_notes = models.TextField(blank=True)

    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-registered_at"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"


class ConsentRecord(models.Model):
    """
    Audit trail for required/optional consents at registration or later.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="consents",
    )
    consent_type = models.CharField(max_length=32, choices=ConsentType.choices)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_consents",
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "consent_type"],
                name="students_unique_student_consent_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_id} {self.consent_type}={self.accepted}"
