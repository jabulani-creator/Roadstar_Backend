"""Read queries for leads — staff inbox; public never lists leads."""

from __future__ import annotations

from django.db.models import Count, QuerySet

from leads.models import Lead, LeadStatus


def leads_staff(
    *,
    status: str | None = None,
    assigned_to_id: int | None = None,
) -> QuerySet[Lead]:
    qs = Lead.objects.select_related(
        "preferred_branch",
        "interested_course",
        "recommended_course",
        "assigned_to",
    ).all()
    if status:
        qs = qs.filter(status=status)
    if assigned_to_id is not None:
        qs = qs.filter(assigned_to_id=assigned_to_id)
    return qs.order_by("-created_at")


def lead_by_id(*, lead_id: int) -> Lead | None:
    return (
        Lead.objects.select_related(
            "preferred_branch",
            "interested_course",
            "recommended_course",
            "assigned_to",
        )
        .filter(pk=lead_id)
        .first()
    )


def lead_inbox_stats() -> dict:
    """Simple counts for dashboard overview."""
    rows = Lead.objects.values("status").annotate(total=Count("id"))
    by_status = {row["status"]: row["total"] for row in rows}
    open_statuses = {
        LeadStatus.NEW,
        LeadStatus.CONTACTED,
        LeadStatus.RECOMMENDED,
        LeadStatus.QUOTE_PENDING,
    }
    return {
        "by_status": by_status,
        "open_count": sum(by_status.get(s, 0) for s in open_statuses),
        "new_count": by_status.get(LeadStatus.NEW, 0),
        "converted_count": by_status.get(LeadStatus.CONVERTED, 0),
        "lost_count": by_status.get(LeadStatus.LOST, 0),
        "total": Lead.objects.count(),
    }
