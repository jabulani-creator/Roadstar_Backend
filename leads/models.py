"""
Durable data for the `leads` domain.

Owns: structured enquiries, referral source, status/assignment/conversion.

Plain English:
- Lead = a prospect who asked about training (form or WhatsApp handoff).
- Staff manage the inbox: contact → recommend → quote → convert or lose.
- WhatsApp *links* are frontend-only; stored lead records live here.

Does NOT own: student profiles, payments, lesson bookings, course prices.
"""

from django.conf import settings
from django.db import models


class LeadStatus(models.TextChoices):
    """
    Lifecycle from checklist / eng design:
    new → contacted → recommended → quote_pending → converted | lost
    """

    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    RECOMMENDED = "recommended", "Recommended"
    QUOTE_PENDING = "quote_pending", "Quote / registration pending"
    CONVERTED = "converted", "Converted"
    LOST = "lost", "Lost"


class ReferralSource(models.TextChoices):
    WEBSITE = "website", "Website"
    WHATSAPP = "whatsapp", "WhatsApp"
    WALK_IN = "walk_in", "Walk-in"
    REFERRAL = "referral", "Friend / family referral"
    SOCIAL = "social", "Social media"
    GOOGLE = "google", "Google / search"
    OTHER = "other", "Other"


class LeadChannel(models.TextChoices):
    """Where the structured payload came from."""

    CONTACT_FORM = "contact_form", "Contact form"
    FIND_YOUR_COURSE = "find_your_course", "Find your course"
    WHATSAPP_HANDOFF = "whatsapp_handoff", "WhatsApp handoff"
    REGISTER_INTEREST = "register_interest", "Register interest"
    OTHER = "other", "Other"


class ExperienceLevel(models.TextChoices):
    BEGINNER = "beginner", "Complete beginner"
    SOME = "some", "Some experience"
    LICENSED_REFRESHER = "licensed_refresher", "Licensed / refresher"
    PROFESSIONAL = "professional", "Professional / fleet"
    UNSURE = "unsure", "Not sure"


class LicenceClassInterest(models.TextChoices):
    CLASS_B = "B", "Class B"
    CLASS_C1 = "C1", "Class C1"
    CLASS_C = "C", "Class C"
    OTHER = "other", "Other / specialised"
    UNSURE = "unsure", "Not sure"


class TransmissionInterest(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTOMATIC = "automatic", "Automatic"
    EITHER = "either", "Either / no preference"
    UNSURE = "unsure", "Not sure"


class Lead(models.Model):
    """
    Structured prospect enquiry for the staff inbox.
    """

    # Identity
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    preferred_contact = models.CharField(
        max_length=32,
        blank=True,
        help_text="Optional note, e.g. WhatsApp after 17:00.",
    )

    # Training need
    experience_level = models.CharField(
        max_length=32,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.UNSURE,
    )
    licence_class = models.CharField(
        max_length=16,
        choices=LicenceClassInterest.choices,
        default=LicenceClassInterest.UNSURE,
    )
    transmission = models.CharField(
        max_length=16,
        choices=TransmissionInterest.choices,
        default=TransmissionInterest.UNSURE,
    )
    preferred_branch = models.ForeignKey(
        "catalogue.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
    )
    preferred_schedule = models.CharField(
        max_length=255,
        blank=True,
        help_text="Free text, e.g. weekday evenings / Saturdays.",
    )
    message = models.TextField(blank=True)

    # Recommendation / course interest
    interested_course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
    )
    recommended_course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recommended_leads",
    )

    # Capture metadata
    channel = models.CharField(
        max_length=32,
        choices=LeadChannel.choices,
        default=LeadChannel.CONTACT_FORM,
    )
    referral_source = models.CharField(
        max_length=32,
        choices=ReferralSource.choices,
        default=ReferralSource.WEBSITE,
    )
    referral_detail = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional free text, e.g. referrer name or campaign.",
    )
    whatsapp_summary = models.TextField(
        blank=True,
        help_text="Pre-filled WhatsApp text the prospect was offered (for inbox context).",
    )

    # Lifecycle
    status = models.CharField(
        max_length=32,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
    )
    internal_notes = models.TextField(
        blank=True,
        help_text="Staff follow-up notes (not shown publicly).",
    )
    lost_reason = models.CharField(max_length=255, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    # Placeholder until `students` owns registration linkage.
    converted_student_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional student id after students domain lands.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_status_display()})"
