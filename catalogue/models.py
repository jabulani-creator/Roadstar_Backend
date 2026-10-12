"""
Durable data for the `catalogue` domain.

Owns: branches/locations, courses/packages, promotions.

Plain English:
- Branch = a physical Roadstar place (Emmasdale, Thornpark).
- Course = a sellable training offer with fee and suitability info.
- Promotion = a dated discount/offer that must expire.

Does NOT own: payments, student records, lesson bookings, FAQs.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class PublishStatus(models.TextChoices):
    """Shared publishing states for catalogue records."""

    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    INACTIVE = "inactive", "Inactive"


class LicenceClass(models.TextChoices):
    CLASS_B = "B", "Class B"
    CLASS_C1 = "C1", "Class D / C1"
    CLASS_C = "C", "Class C"
    OTHER = "other", "Other / specialised"


class Transmission(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTOMATIC = "automatic", "Automatic"
    BOTH = "both", "Manual and automatic"


class CourseLevel(models.TextChoices):
    BEGINNER_FULL = "beginner_full", "Beginner / Full course"
    STANDARD = "standard", "Standard course"
    HALF = "half", "Half course"
    REFRESHER = "refresher", "Refresher"
    TEST_PREP = "test_prep", "Test preparation"
    PROFESSIONAL = "professional", "Professional / fleet"
    OTHER = "other", "Other"


class Branch(models.Model):
    """
    A Roadstar teaching location.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=140)
    address = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    map_url = models.URLField(blank=True, help_text="Google Maps or similar link.")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    operating_hours = models.CharField(max_length=255, blank=True)
    primary_phone = models.CharField(max_length=32, blank=True)
    secondary_phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    classes_available_note = models.TextField(
        blank=True,
        help_text="Human note of classes/transmissions offered at this branch.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "branches"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Course(models.Model):
    """
    A publishable training package / fee card.
    """

    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, max_length=180)
    summary = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short card text: who this course is for.",
    )
    description = models.TextField(blank=True)
    licence_class = models.CharField(
        max_length=16,
        choices=LicenceClass.choices,
        default=LicenceClass.CLASS_B,
    )
    transmission = models.CharField(
        max_length=16,
        choices=Transmission.choices,
        default=Transmission.BOTH,
    )
    level = models.CharField(
        max_length=32,
        choices=CourseLevel.choices,
        default=CourseLevel.BEGINNER_FULL,
    )
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Public duration ladder value, e.g. 20 / 15 / 10 / 7.",
    )
    min_age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum learner age for this package, if published.",
    )
    max_gvm_kg = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum GVM (kg) associated with the licence class, if published.",
    )
    lesson_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of practical lessons if defined.",
    )
    lesson_unit_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Configurable lesson length. Do not hard-code 30.",
    )
    price_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Roadstar tuition only. Leave blank to show request-quote.",
    )
    currency = models.CharField(max_length=8, default="ZMW")
    show_price = models.BooleanField(
        default=True,
        help_text="If false, public UI should show request confirmed quote.",
    )
    inclusions = models.TextField(blank=True)
    exclusions = models.TextField(
        blank=True,
        help_text="Including reminder that RTSA statutory fees are separate.",
    )
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    price_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time tuition/price fields were confirmed.",
    )
    branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name="courses",
        help_text="Branches where this course is offered.",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_courses",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["licence_class", "level", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "course"
            slug = base
            n = 2
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_public(self) -> bool:
        return self.status == PublishStatus.APPROVED


class Promotion(models.Model):
    """
    Dated commercial offer. Must not stay active forever.
    """

    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, max_length=180)
    summary = models.CharField(max_length=255, blank=True)
    terms = models.TextField(blank=True)
    discount_label = models.CharField(
        max_length=80,
        blank=True,
        help_text="Display text such as 15% off or K500 off.",
    )
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name="promotions",
        help_text="Leave empty if promotion applies broadly and copy explains it.",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def is_currently_active(self) -> bool:
        """Approved and inside the date window."""
        if self.status != PublishStatus.APPROVED:
            return False
        now = timezone.now()
        return self.starts_at <= now <= self.ends_at
