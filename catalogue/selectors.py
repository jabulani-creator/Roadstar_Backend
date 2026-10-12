"""
Read/query helpers for `catalogue`.

Plain English:
- Selectors fetch the right branches/courses/promotions.
- Public queries only return approved (and currently active) records.
- Staff queries can include drafts for the dashboard.
"""

from django.db.models import Prefetch, QuerySet
from django.utils import timezone

from .models import Branch, Course, Promotion, PublishStatus


def get_branch_queryset() -> QuerySet[Branch]:
    return Branch.objects.all()


def get_public_branches() -> QuerySet[Branch]:
    """Active branches for public location pages."""
    return get_branch_queryset().filter(is_active=True)


def get_branch_by_slug(slug: str, *, public_only: bool = False) -> Branch | None:
    qs = get_public_branches() if public_only else get_branch_queryset()
    return qs.filter(slug=slug).first()


def get_course_queryset() -> QuerySet[Course]:
    """
    Base course query with branches prefetched to avoid N+1 queries.
    """
    return Course.objects.prefetch_related(
        Prefetch("branches", queryset=Branch.objects.filter(is_active=True).order_by("name"))
    )


def get_public_courses() -> QuerySet[Course]:
    """Courses approved for the public website."""
    return get_course_queryset().filter(status=PublishStatus.APPROVED)


def get_staff_courses() -> QuerySet[Course]:
    """All courses for dashboard management."""
    return get_course_queryset()


def get_course_by_slug(slug: str, *, public_only: bool = False) -> Course | None:
    qs = get_public_courses() if public_only else get_course_queryset()
    return qs.filter(slug=slug).first()


def get_promotion_queryset() -> QuerySet[Promotion]:
    return Promotion.objects.prefetch_related(
        Prefetch(
            "courses",
            queryset=get_public_courses(),
        )
    )


def get_public_promotions() -> QuerySet[Promotion]:
    """
    Approved promotions that are inside their date window right now.
    """
    now = timezone.now()
    return get_promotion_queryset().filter(
        status=PublishStatus.APPROVED,
        starts_at__lte=now,
        ends_at__gte=now,
    )


def get_staff_promotions() -> QuerySet[Promotion]:
    return get_promotion_queryset()


def get_promotion_by_slug(slug: str, *, public_only: bool = False) -> Promotion | None:
    if public_only:
        return get_public_promotions().filter(slug=slug).first()
    return get_promotion_queryset().filter(slug=slug).first()
