"""
Durable data for the `content` domain.

Owns: FAQs, RTSA guidance, articles/guides, resources, testimonials.

Plain English:
- FAQ = common prospect questions.
- RTSAGuidance = dated government-process / statutory-fee notes (not Roadstar tuition).
- Article = long-form guide or learning-centre preview.
- Resource = downloadable checklist/PDF link.
- Testimonial = student proof with publish consent.

Does NOT own: course prices, payments, leads, bookings.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class PublishStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    INACTIVE = "inactive", "Inactive"


class FAQCategory(models.TextChoices):
    COURSES = "courses", "Courses & fees"
    ENROLMENT = "enrolment", "Enrolment & documents"
    LESSONS = "lessons", "Lessons & scheduling"
    RTSA = "rtsa", "RTSA & licensing"
    GENERAL = "general", "General"


class ArticleType(models.TextChoices):
    GUIDE = "guide", "Guide"
    LEARNING_PREVIEW = "learning_preview", "Learning centre preview"
    POLICY = "policy", "Policy"


class ResourceVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal / staff only"


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(
        max_length=32,
        choices=FAQCategory.choices,
        default=FAQCategory.GENERAL,
    )
    display_order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_faqs",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "display_order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self) -> str:
        return self.question


class RTSAGuidance(models.Model):
    """
    Dated RTSA / licence-process information.

    Keep Roadstar tuition out of this model — that lives in catalogue.Course.
    """

    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, max_length=180)
    body = models.TextField()
    fee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional statutory fee amount, if publishing one.",
    )
    currency = models.CharField(max_length=8, default="ZMW")
    source_url = models.URLField(
        blank=True,
        help_text="Link to official RTSA (or related) source.",
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the fee/process info became effective.",
    )
    last_reviewed_at = models.DateField(
        null=True,
        blank=True,
        help_text="When Roadstar last checked this against the source.",
    )
    display_order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_rtsa_guidance",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "title"]
        verbose_name = "RTSA guidance"
        verbose_name_plural = "RTSA guidance"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Article(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, max_length=200)
    summary = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    article_type = models.CharField(
        max_length=32,
        choices=ArticleType.choices,
        default=ArticleType.GUIDE,
    )
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_articles",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class ResourceCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True, max_length=140)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "resource categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Resource(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, max_length=200)
    summary = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(
        ResourceCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resources",
    )
    # Prefer external/hosted file URL for now (simple). Upload field can come later.
    file_url = models.URLField(blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=ResourceVisibility.choices,
        default=ResourceVisibility.PUBLIC,
    )
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_resources",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Testimonial(models.Model):
    """
    Student success / proof quote.

    Requires consent before public approval.
    """

    quote = models.TextField()
    author_name = models.CharField(max_length=120)
    author_role = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional, e.g. Class B graduate.",
    )
    related_course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="testimonials",
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Optional 1-5 rating.",
    )
    consent_to_publish = models.BooleanField(
        default=False,
        help_text="Must be true before public approval.",
    )
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_testimonials",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.author_name}: {self.quote[:40]}"
