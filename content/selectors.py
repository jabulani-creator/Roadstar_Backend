"""Read queries for content — public only sees approved items."""

from __future__ import annotations

from django.db.models import QuerySet

from content.models import (
    FAQ,
    Article,
    PublishStatus,
    Resource,
    ResourceCategory,
    ResourceVisibility,
    RTSAGuidance,
    Testimonial,
)


def faqs_public() -> QuerySet[FAQ]:
    return FAQ.objects.filter(status=PublishStatus.APPROVED).order_by(
        "category", "display_order", "id"
    )


def faqs_staff() -> QuerySet[FAQ]:
    return FAQ.objects.all().order_by("category", "display_order", "id")


def faq_by_id(*, faq_id: int) -> FAQ | None:
    return FAQ.objects.filter(pk=faq_id).first()


def rtsa_public() -> QuerySet[RTSAGuidance]:
    return RTSAGuidance.objects.filter(status=PublishStatus.APPROVED).order_by(
        "display_order", "title"
    )


def rtsa_staff() -> QuerySet[RTSAGuidance]:
    return RTSAGuidance.objects.all().order_by("display_order", "title")


def rtsa_by_slug(*, slug: str) -> RTSAGuidance | None:
    return RTSAGuidance.objects.filter(slug=slug).first()


def articles_public() -> QuerySet[Article]:
    return Article.objects.filter(status=PublishStatus.APPROVED).order_by(
        "-updated_at"
    )


def articles_staff() -> QuerySet[Article]:
    return Article.objects.all().order_by("-updated_at")


def article_by_slug(*, slug: str) -> Article | None:
    return Article.objects.filter(slug=slug).first()


def resource_categories() -> QuerySet[ResourceCategory]:
    return ResourceCategory.objects.all().order_by("name")


def resource_category_by_slug(*, slug: str) -> ResourceCategory | None:
    return ResourceCategory.objects.filter(slug=slug).first()


def resources_public() -> QuerySet[Resource]:
    return (
        Resource.objects.select_related("category")
        .filter(
            status=PublishStatus.APPROVED,
            visibility=ResourceVisibility.PUBLIC,
        )
        .order_by("title")
    )


def resources_staff() -> QuerySet[Resource]:
    return (
        Resource.objects.select_related("category")
        .all()
        .order_by("title")
    )


def resource_by_slug(*, slug: str) -> Resource | None:
    return (
        Resource.objects.select_related("category")
        .filter(slug=slug)
        .first()
    )


def testimonials_public() -> QuerySet[Testimonial]:
    return (
        Testimonial.objects.select_related("related_course")
        .filter(
            status=PublishStatus.APPROVED,
            consent_to_publish=True,
        )
        .order_by("-created_at")
    )


def testimonials_staff() -> QuerySet[Testimonial]:
    return (
        Testimonial.objects.select_related("related_course")
        .all()
        .order_by("-created_at")
    )


def testimonial_by_id(*, testimonial_id: int) -> Testimonial | None:
    return (
        Testimonial.objects.select_related("related_course")
        .filter(pk=testimonial_id)
        .first()
    )
