"""
Durable data for the `learning` domain.

Owns: practice topics, question bank, practice papers, student attempts.

Plain English:
- PracticePaper = a mock / past-paper-style set Roadstar publishes.
- Question = one multiple-choice item with an explanation.
- Attempt = a student sitting a paper (timed, scored).
- StudyDocument = optional PDF/link staff mark as rights-cleared.

Does NOT own: RTSA official exam reproduction, commerce payments, bookings.
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


class Difficulty(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"


class Topic(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True, max_length=140)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Question(models.Model):
    """
    Roadstar-authored (or rights-cleared) multiple-choice question.
    """

    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,
        related_name="questions",
    )
    prompt = models.TextField()
    choice_a = models.CharField(max_length=500)
    choice_b = models.CharField(max_length=500)
    choice_c = models.CharField(max_length=500, blank=True)
    choice_d = models.CharField(max_length=500, blank=True)
    correct_choice = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
    )
    explanation = models.TextField(
        blank=True,
        help_text="Shown after the attempt is submitted / reviewed.",
    )
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
    )
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    is_rights_cleared = models.BooleanField(
        default=True,
        help_text="Must be true for Roadstar-authored or cleared content.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="authored_questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["topic__sort_order", "id"]

    def __str__(self) -> str:
        return self.prompt[:80]


class PracticePaper(models.Model):
    """
    A practice / mock paper (set of questions), not an official RTSA reprint.
    """

    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, max_length=200)
    summary = models.CharField(max_length=255, blank=True)
    instructions = models.TextField(blank=True)
    time_limit_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional timer. Blank = untimed practice.",
    )
    pass_mark_percent = models.PositiveIntegerField(
        default=50,
        help_text="Percent required to mark the attempt as passed.",
    )
    shuffle_questions = models.BooleanField(default=True)
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
    available_to_public_preview = models.BooleanField(
        default=False,
        help_text="If true, paper metadata is visible publicly; sitting still needs login.",
    )
    questions = models.ManyToManyField(
        Question,
        through="PracticePaperQuestion",
        related_name="papers",
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_practice_papers",
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


class PracticePaperQuestion(models.Model):
    paper = models.ForeignKey(
        PracticePaper,
        on_delete=models.CASCADE,
        related_name="paper_questions",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="paper_links",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["paper", "question"],
                name="learning_unique_paper_question",
            )
        ]

    def __str__(self) -> str:
        return f"{self.paper_id} → Q{self.question_id}"


class StudyDocument(models.Model):
    """
    Optional downloadable study PDF/link. Staff must confirm rights clearance.
    """

    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, max_length=200)
    summary = models.CharField(max_length=255, blank=True)
    file_url = models.URLField()
    topic = models.ForeignKey(
        Topic,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="study_documents",
    )
    is_rights_cleared = models.BooleanField(
        default=False,
        help_text="Must be true before approval for student/public use.",
    )
    status = models.CharField(
        max_length=32,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )
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


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In progress"
    SUBMITTED = "submitted", "Submitted"
    EXPIRED = "expired", "Expired (time up)"


class Attempt(models.Model):
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="learning_attempts",
    )
    paper = models.ForeignKey(
        PracticePaper,
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    status = models.CharField(
        max_length=32,
        choices=AttemptStatus.choices,
        default=AttemptStatus.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score_correct = models.PositiveIntegerField(default=0)
    score_total = models.PositiveIntegerField(default=0)
    score_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    passed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Attempt #{self.pk} {self.student_id} / {self.paper_id}"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="attempt_answers",
    )
    selected_choice = models.CharField(
        max_length=1,
        blank=True,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("", "Blank")],
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="learning_unique_attempt_question",
            )
        ]

    def __str__(self) -> str:
        return f"Attempt {self.attempt_id} Q{self.question_id}={self.selected_choice}"
