"""
Write workflows for `content`.

Plain English:
- Creating, updating, approving, and rejecting FAQs/articles/resources/etc.
  happens here so views stay thin and rules stay consistent.
- Testimonials cannot be approved without publish consent.
"""

from __future__ import annotations

from django.utils import timezone
from django.utils.text import slugify

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role

from .models import (
    FAQ,
    Article,
    PublishStatus,
    Resource,
    ResourceCategory,
    RTSAGuidance,
    Testimonial,
)


class ContentServiceError(Exception):
    """Domain error with a safe API message."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


PROTECTED_FIELDS = frozenset(
    {"slug", "status", "approved_by", "approved_at", "created_at", "updated_at"}
)


def _can_manage(user: User) -> bool:
    return user_has_any_role(user, [StaffRole.OWNER, StaffRole.CONTENT]) or user.is_superuser


def _require_manager(actor: User) -> None:
    if not _can_manage(actor):
        raise ContentServiceError("Not allowed to manage content.", code="forbidden")


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


def _apply_fields(instance, data: dict, *, skip: frozenset[str] = PROTECTED_FIELDS) -> None:
    for field, value in data.items():
        if field in skip:
            continue
        setattr(instance, field, value)


def _approve(instance, *, actor: User) -> None:
    instance.status = PublishStatus.APPROVED
    instance.approved_by = actor
    instance.approved_at = timezone.now()
    instance.save(
        update_fields=["status", "approved_by", "approved_at", "updated_at"]
    )


def _reject(instance) -> None:
    instance.status = PublishStatus.REJECTED
    instance.approved_by = None
    instance.approved_at = None
    instance.save(
        update_fields=["status", "approved_by", "approved_at", "updated_at"]
    )


def _submit(instance) -> None:
    if instance.status not in {
        PublishStatus.DRAFT,
        PublishStatus.REJECTED,
        PublishStatus.PENDING_REVIEW,
    }:
        raise ContentServiceError(
            "Only draft/rejected items can be submitted for review.",
            code="invalid_status",
        )
    instance.status = PublishStatus.PENDING_REVIEW
    instance.save(update_fields=["status", "updated_at"])


def _deactivate(instance) -> None:
    instance.status = PublishStatus.INACTIVE
    instance.save(update_fields=["status", "updated_at"])


# --- FAQ ---


def create_faq(*, actor: User, data: dict) -> FAQ:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    payload.setdefault("status", PublishStatus.DRAFT)
    return FAQ.objects.create(**payload)


def update_faq(*, actor: User, faq: FAQ, data: dict) -> FAQ:
    _require_manager(actor)
    _apply_fields(faq, data)
    faq.save()
    return faq


def submit_faq(*, actor: User, faq: FAQ) -> FAQ:
    _require_manager(actor)
    _submit(faq)
    return faq


def approve_faq(*, actor: User, faq: FAQ) -> FAQ:
    _require_manager(actor)
    _approve(faq, actor=actor)
    return faq


def reject_faq(*, actor: User, faq: FAQ, note: str = "") -> FAQ:
    _require_manager(actor)
    _ = note
    _reject(faq)
    return faq


def deactivate_faq(*, actor: User, faq: FAQ) -> FAQ:
    _require_manager(actor)
    _deactivate(faq)
    return faq


# --- RTSA guidance ---


def create_rtsa(*, actor: User, data: dict) -> RTSAGuidance:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    title = payload.get("title") or ""
    payload.setdefault("slug", _unique_slug(RTSAGuidance, title))
    payload.setdefault("status", PublishStatus.DRAFT)
    return RTSAGuidance.objects.create(**payload)


def update_rtsa(*, actor: User, item: RTSAGuidance, data: dict) -> RTSAGuidance:
    _require_manager(actor)
    _apply_fields(item, data)
    item.save()
    return item


def submit_rtsa(*, actor: User, item: RTSAGuidance) -> RTSAGuidance:
    _require_manager(actor)
    _submit(item)
    return item


def approve_rtsa(*, actor: User, item: RTSAGuidance) -> RTSAGuidance:
    _require_manager(actor)
    _approve(item, actor=actor)
    return item


def reject_rtsa(*, actor: User, item: RTSAGuidance, note: str = "") -> RTSAGuidance:
    _require_manager(actor)
    _ = note
    _reject(item)
    return item


def deactivate_rtsa(*, actor: User, item: RTSAGuidance) -> RTSAGuidance:
    _require_manager(actor)
    _deactivate(item)
    return item


# --- Articles ---


def create_article(*, actor: User, data: dict) -> Article:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    title = payload.get("title") or ""
    payload.setdefault("slug", _unique_slug(Article, title))
    payload.setdefault("status", PublishStatus.DRAFT)
    return Article.objects.create(**payload)


def update_article(*, actor: User, article: Article, data: dict) -> Article:
    _require_manager(actor)
    _apply_fields(article, data)
    article.save()
    return article


def submit_article(*, actor: User, article: Article) -> Article:
    _require_manager(actor)
    _submit(article)
    return article


def approve_article(*, actor: User, article: Article) -> Article:
    _require_manager(actor)
    _approve(article, actor=actor)
    return article


def reject_article(*, actor: User, article: Article, note: str = "") -> Article:
    _require_manager(actor)
    _ = note
    _reject(article)
    return article


def deactivate_article(*, actor: User, article: Article) -> Article:
    _require_manager(actor)
    _deactivate(article)
    return article


# --- Resource categories ---


def create_resource_category(*, actor: User, data: dict) -> ResourceCategory:
    _require_manager(actor)
    payload = dict(data)
    name = payload.get("name") or ""
    payload.setdefault("slug", _unique_slug(ResourceCategory, name))
    return ResourceCategory.objects.create(**payload)


def update_resource_category(
    *, actor: User, category: ResourceCategory, data: dict
) -> ResourceCategory:
    _require_manager(actor)
    _apply_fields(category, data, skip=frozenset({"slug"}))
    category.save()
    return category


# --- Resources ---


def create_resource(*, actor: User, data: dict) -> Resource:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    title = payload.get("title") or ""
    payload.setdefault("slug", _unique_slug(Resource, title))
    payload.setdefault("status", PublishStatus.DRAFT)
    return Resource.objects.create(**payload)


def update_resource(*, actor: User, resource: Resource, data: dict) -> Resource:
    _require_manager(actor)
    _apply_fields(resource, data)
    resource.save()
    return resource


def submit_resource(*, actor: User, resource: Resource) -> Resource:
    _require_manager(actor)
    _submit(resource)
    return resource


def approve_resource(*, actor: User, resource: Resource) -> Resource:
    _require_manager(actor)
    _approve(resource, actor=actor)
    return resource


def reject_resource(*, actor: User, resource: Resource, note: str = "") -> Resource:
    _require_manager(actor)
    _ = note
    _reject(resource)
    return resource


def deactivate_resource(*, actor: User, resource: Resource) -> Resource:
    _require_manager(actor)
    _deactivate(resource)
    return resource


# --- Testimonials ---


def _validate_rating(rating) -> None:
    if rating is None:
        return
    if rating < 1 or rating > 5:
        raise ContentServiceError(
            "Rating must be between 1 and 5.",
            code="invalid_rating",
        )


def create_testimonial(*, actor: User, data: dict) -> Testimonial:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    _validate_rating(payload.get("rating"))
    payload.setdefault("status", PublishStatus.DRAFT)
    return Testimonial.objects.create(**payload)


def update_testimonial(
    *, actor: User, testimonial: Testimonial, data: dict
) -> Testimonial:
    _require_manager(actor)
    payload = dict(data)
    if "rating" in payload:
        _validate_rating(payload.get("rating"))
    _apply_fields(testimonial, payload)
    # Removing consent unpublishes an approved quote.
    if (
        testimonial.status == PublishStatus.APPROVED
        and not testimonial.consent_to_publish
    ):
        testimonial.status = PublishStatus.INACTIVE
        testimonial.approved_by = None
        testimonial.approved_at = None
    testimonial.save()
    return testimonial


def submit_testimonial(*, actor: User, testimonial: Testimonial) -> Testimonial:
    _require_manager(actor)
    _submit(testimonial)
    return testimonial


def approve_testimonial(*, actor: User, testimonial: Testimonial) -> Testimonial:
    _require_manager(actor)
    if not testimonial.consent_to_publish:
        raise ContentServiceError(
            "Cannot approve a testimonial without publish consent.",
            code="consent_required",
        )
    _approve(testimonial, actor=actor)
    return testimonial


def reject_testimonial(
    *, actor: User, testimonial: Testimonial, note: str = ""
) -> Testimonial:
    _require_manager(actor)
    _ = note
    _reject(testimonial)
    return testimonial


def deactivate_testimonial(*, actor: User, testimonial: Testimonial) -> Testimonial:
    _require_manager(actor)
    _deactivate(testimonial)
    return testimonial
