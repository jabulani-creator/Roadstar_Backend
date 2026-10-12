"""
Write workflows for `catalogue`.

Plain English:
- Creating, updating, approving, and rejecting courses/branches/promotions
  happens here so views stay thin and rules stay consistent.
"""

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role, user_has_role

from .models import Branch, Course, Promotion, PublishStatus


class CatalogueServiceError(Exception):
    """Domain error with a safe API message."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _can_publish(user: User) -> bool:
    return user_has_any_role(user, [StaffRole.OWNER, StaffRole.CONTENT]) or user.is_superuser


def _unique_slug(model, base: str, *, exclude_pk=None) -> str:
    base = slugify(base) or model.__name__.lower()
    slug = base
    n = 2
    while True:
        qs = model.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return slug
        slug = f"{base}-{n}"
        n += 1


def create_branch(*, actor: User, data: dict) -> Branch:
    if not user_has_any_role(actor, [StaffRole.OWNER, StaffRole.CONTENT, StaffRole.RECEPTION]) and not actor.is_superuser:
        raise CatalogueServiceError("Not allowed to manage branches.", code="forbidden")

    payload = dict(data)
    name = payload.get("name") or ""
    payload.setdefault("slug", _unique_slug(Branch, name))
    return Branch.objects.create(**payload)


def update_branch(*, actor: User, branch: Branch, data: dict) -> Branch:
    if not user_has_any_role(actor, [StaffRole.OWNER, StaffRole.CONTENT, StaffRole.RECEPTION]) and not actor.is_superuser:
        raise CatalogueServiceError("Not allowed to manage branches.", code="forbidden")

    for field, value in data.items():
        if field == "slug":
            continue
        setattr(branch, field, value)
    branch.save()
    return branch


@transaction.atomic
def create_course(*, actor: User, data: dict) -> Course:
    if not user_has_any_role(actor, [StaffRole.OWNER, StaffRole.CONTENT]) and not actor.is_superuser:
        raise CatalogueServiceError("Not allowed to manage courses.", code="forbidden")

    payload = dict(data)
    branch_ids = payload.pop("branches", None)
    name = payload.get("name") or ""
    payload.setdefault("slug", _unique_slug(Course, name))
    payload.setdefault("status", PublishStatus.DRAFT)

    if payload.get("price_amount") is not None or payload.get("show_price") is not None:
        payload["price_updated_at"] = timezone.now()

    course = Course.objects.create(**payload)
    if branch_ids is not None:
        course.branches.set(branch_ids)
    return course


@transaction.atomic
def update_course(*, actor: User, course: Course, data: dict) -> Course:
    if not user_has_any_role(actor, [StaffRole.OWNER, StaffRole.CONTENT]) and not actor.is_superuser:
        raise CatalogueServiceError("Not allowed to manage courses.", code="forbidden")

    payload = dict(data)
    branch_ids = payload.pop("branches", None)
    price_touched = any(key in payload for key in ("price_amount", "show_price", "currency"))

    was_approved = course.status == PublishStatus.APPROVED

    for field, value in payload.items():
        if field in {"slug", "approved_by", "approved_at", "status"}:
            continue
        setattr(course, field, value)

    if price_touched:
        course.price_updated_at = timezone.now()

    # Non-owners editing a live public course must go through review again.
    if was_approved and not user_has_role(actor, StaffRole.OWNER) and not actor.is_superuser:
        course.status = PublishStatus.PENDING_REVIEW
        course.approved_by = None
        course.approved_at = None

    course.save()
    if branch_ids is not None:
        course.branches.set(branch_ids)
    return course


def submit_course_for_review(*, actor: User, course: Course) -> Course:
    if not user_has_any_role(actor, [StaffRole.OWNER, StaffRole.CONTENT]) and not actor.is_superuser:
        raise CatalogueServiceError("Not allowed to submit courses.", code="forbidden")
    if course.status not in {PublishStatus.DRAFT, PublishStatus.REJECTED, PublishStatus.PENDING_REVIEW}:
        raise CatalogueServiceError(
            "Only draft/rejected courses can be submitted for review.",
            code="invalid_status",
        )
    course.status = PublishStatus.PENDING_REVIEW
    course.save(update_fields=["status", "updated_at"])
    return course


def approve_course(*, actor: User, course: Course) -> Course:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to approve courses.", code="forbidden")

    course.status = PublishStatus.APPROVED
    course.approved_by = actor
    course.approved_at = timezone.now()
    if course.price_updated_at is None and course.price_amount is not None:
        course.price_updated_at = timezone.now()
    course.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "price_updated_at",
            "updated_at",
        ]
    )
    return course


def reject_course(*, actor: User, course: Course, note: str = "") -> Course:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to reject courses.", code="forbidden")

    course.status = PublishStatus.REJECTED
    course.approved_by = None
    course.approved_at = None
    course.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    # note reserved for a future audit log; keep signature stable.
    _ = note
    return course


def deactivate_course(*, actor: User, course: Course) -> Course:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to deactivate courses.", code="forbidden")
    course.status = PublishStatus.INACTIVE
    course.save(update_fields=["status", "updated_at"])
    return course


@transaction.atomic
def create_promotion(*, actor: User, data: dict) -> Promotion:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to manage promotions.", code="forbidden")

    payload = dict(data)
    course_ids = payload.pop("courses", None)
    title = payload.get("title") or ""
    payload.setdefault("slug", _unique_slug(Promotion, title))
    payload.setdefault("status", PublishStatus.DRAFT)

    if payload.get("ends_at") and payload.get("starts_at") and payload["ends_at"] <= payload["starts_at"]:
        raise CatalogueServiceError(
            "Promotion end time must be after start time.",
            code="invalid_date_range",
        )

    promotion = Promotion.objects.create(**payload)
    if course_ids is not None:
        promotion.courses.set(course_ids)
    return promotion


@transaction.atomic
def update_promotion(*, actor: User, promotion: Promotion, data: dict) -> Promotion:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to manage promotions.", code="forbidden")

    payload = dict(data)
    course_ids = payload.pop("courses", None)

    for field, value in payload.items():
        if field in {"slug", "status"}:
            continue
        setattr(promotion, field, value)

    if promotion.ends_at <= promotion.starts_at:
        raise CatalogueServiceError(
            "Promotion end time must be after start time.",
            code="invalid_date_range",
        )

    promotion.save()
    if course_ids is not None:
        promotion.courses.set(course_ids)
    return promotion


def approve_promotion(*, actor: User, promotion: Promotion) -> Promotion:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to approve promotions.", code="forbidden")
    if promotion.ends_at <= promotion.starts_at:
        raise CatalogueServiceError(
            "Promotion end time must be after start time.",
            code="invalid_date_range",
        )
    promotion.status = PublishStatus.APPROVED
    promotion.save(update_fields=["status", "updated_at"])
    return promotion


def reject_promotion(*, actor: User, promotion: Promotion) -> Promotion:
    if not _can_publish(actor):
        raise CatalogueServiceError("Not allowed to reject promotions.", code="forbidden")
    promotion.status = PublishStatus.REJECTED
    promotion.save(update_fields=["status", "updated_at"])
    return promotion
