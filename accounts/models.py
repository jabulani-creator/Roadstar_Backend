"""
Durable data for the `accounts` domain.

Owns: users, login identity, staff role assignments.

Plain English:
- User = a login account (student, instructor, receptionist, owner, etc.).
- StaffRoleAssignment = which job badge(s) that person holds at Roadstar.
- Detailed student training records belong in `students` later.
- Instructor vehicle/class eligibility belongs in `fleet` later.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Creates users with email as the main login field.

    Django's default manager expects a username. We override that so
    staff/students sign in with email instead.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Roadstar login account.

    Why custom?
    - Email login matches how people actually contact Roadstar.
    - One account type for students, instructors, and staff (roles decide access).
    """

    # We login with email, so Django's username field is unused.
    username = None

    email = models.EmailField(
        unique=True,
        help_text="Primary login identity. Must be unique.",
    )
    phone = models.CharField(
        max_length=32,
        blank=True,
        help_text="Optional contact number (WhatsApp/call).",
    )

    # Public trust-page fields (Instructors & Student Success).
    # Off by default so private staff accounts are never listed accidentally.
    show_on_public_staff_list = models.BooleanField(
        default=False,
        help_text="If true, this person may appear on public staff/instructor pages.",
    )
    public_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Public role label, e.g. Senior Instructor.",
    )
    public_bio = models.TextField(
        blank=True,
        help_text="Short public bio for trust pages.",
    )
    public_list_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first on the public staff list.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        ordering = ["public_list_order", "first_name", "last_name", "email"]

    def __str__(self) -> str:
        return self.email


class StaffRole(models.TextChoices):
    """
    Fixed job badges for dashboard access.

    Kept as choices (not a separate Role table) while the role list is small
    and owned by product docs — avoids inventing a mini role-admin UI too early.
    """

    OWNER = "owner", "Owner / Admin"
    RECEPTION = "reception", "Reception / Scheduler"
    CONTENT = "content", "Content Manager"
    FINANCE = "finance", "Finance Viewer"
    INSTRUCTOR = "instructor", "Instructor"


class StaffRoleAssignment(models.Model):
    """
    Links a user to one staff role.

    A user may have many rows (many roles).
    Example: Morgan could be OWNER and also INSTRUCTOR.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.CharField(
        max_length=32,
        choices=StaffRole.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__email", "role"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="accounts_unique_user_role",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.email} → {self.get_role_display()}"
