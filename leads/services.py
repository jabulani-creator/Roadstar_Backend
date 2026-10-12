"""
Write workflows for `leads`.

Plain English:
- Public may create a lead (no login).
- Staff may assign, note, and move status through a fixed lifecycle.
- Status changes are backend-owned — the frontend cannot invent transitions.
"""

from __future__ import annotations

from django.utils import timezone

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role, user_is_staff_operator
from catalogue.models import Course

from .models import Lead, LeadStatus


class LeadServiceError(Exception):
    """Domain error with a safe API message."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


# Allowed transitions: from_status → frozenset of to_status
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    LeadStatus.NEW: frozenset(
        {LeadStatus.CONTACTED, LeadStatus.LOST, LeadStatus.QUOTE_PENDING}
    ),
    LeadStatus.CONTACTED: frozenset(
        {
            LeadStatus.RECOMMENDED,
            LeadStatus.QUOTE_PENDING,
            LeadStatus.LOST,
            LeadStatus.CONTACTED,
        }
    ),
    LeadStatus.RECOMMENDED: frozenset(
        {
            LeadStatus.QUOTE_PENDING,
            LeadStatus.CONTACTED,
            LeadStatus.LOST,
            LeadStatus.RECOMMENDED,
        }
    ),
    LeadStatus.QUOTE_PENDING: frozenset(
        {
            LeadStatus.CONVERTED,
            LeadStatus.LOST,
            LeadStatus.CONTACTED,
            LeadStatus.QUOTE_PENDING,
        }
    ),
    LeadStatus.CONVERTED: frozenset(),  # terminal
    LeadStatus.LOST: frozenset({LeadStatus.CONTACTED}),  # reopen
}


def _can_manage(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.RECEPTION, StaffRole.CONTENT],
        )
        or user.is_superuser
        or user.is_staff
    )


def _require_manager(actor: User) -> None:
    if not _can_manage(actor):
        raise LeadServiceError("Not allowed to manage leads.", code="forbidden")


def _append_note(lead: Lead, note: str, *, actor: User) -> None:
    note = (note or "").strip()
    if not note:
        return
    stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{stamp} {actor.email}] {note}"
    if lead.internal_notes:
        lead.internal_notes = f"{lead.internal_notes}\n{line}"
    else:
        lead.internal_notes = line


def create_lead(*, data: dict) -> Lead:
    """Public (or staff-assisted) structured enquiry create."""
    payload = dict(data)
    # Never accept staff-controlled fields from the public create path.
    for key in (
        "status",
        "assigned_to",
        "internal_notes",
        "lost_reason",
        "converted_at",
        "converted_student_id",
        "recommended_course",
    ):
        payload.pop(key, None)

    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not full_name:
        raise LeadServiceError("Full name is required.", code="invalid_name")
    if not phone:
        raise LeadServiceError("Phone number is required.", code="invalid_phone")

    payload["full_name"] = full_name
    payload["phone"] = phone
    payload.setdefault("status", LeadStatus.NEW)
    return Lead.objects.create(**payload)


def update_lead(*, actor: User, lead: Lead, data: dict) -> Lead:
    _require_manager(actor)
    if lead.status == LeadStatus.CONVERTED:
        raise LeadServiceError(
            "Converted leads cannot be edited. Reopen is not available from converted.",
            code="terminal_status",
        )

    protected = {
        "status",
        "converted_at",
        "converted_student_id",
        "created_at",
        "updated_at",
    }
    for field, value in data.items():
        if field in protected:
            continue
        setattr(lead, field, value)
    lead.save()
    return lead


def assign_lead(*, actor: User, lead: Lead, assigned_to: User | None) -> Lead:
    _require_manager(actor)
    if assigned_to is not None and not user_is_staff_operator(assigned_to):
        raise LeadServiceError(
            "Assignee must be a staff operator.",
            code="invalid_assignee",
        )
    lead.assigned_to = assigned_to
    lead.save(update_fields=["assigned_to", "updated_at"])
    return lead


def transition_lead(
    *,
    actor: User,
    lead: Lead,
    new_status: str,
    note: str = "",
    lost_reason: str = "",
    recommended_course_id: int | None = None,
) -> Lead:
    _require_manager(actor)

    if new_status not in LeadStatus.values:
        raise LeadServiceError("Unknown lead status.", code="invalid_status")

    allowed = ALLOWED_TRANSITIONS.get(lead.status, frozenset())
    if new_status not in allowed:
        raise LeadServiceError(
            f"Cannot move lead from {lead.status} to {new_status}.",
            code="invalid_transition",
        )

    if new_status == LeadStatus.LOST and not (lost_reason or lead.lost_reason):
        raise LeadServiceError(
            "A lost reason is required when marking a lead lost.",
            code="lost_reason_required",
        )

    if new_status == LeadStatus.RECOMMENDED:
        course_id = recommended_course_id
        if course_id is None and lead.recommended_course_id is None:
            # Fall back to interested course if staff did not pick one.
            course_id = lead.interested_course_id
        if course_id is None:
            raise LeadServiceError(
                "A recommended course is required for this status.",
                code="course_required",
            )
        if not Course.objects.filter(pk=course_id).exists():
            raise LeadServiceError("Recommended course not found.", code="course_not_found")
        lead.recommended_course_id = course_id

    if lost_reason:
        lead.lost_reason = lost_reason.strip()

    _append_note(lead, note, actor=actor)
    lead.status = new_status
    lead.save()
    return lead


def mark_contacted(*, actor: User, lead: Lead, note: str = "") -> Lead:
    return transition_lead(
        actor=actor,
        lead=lead,
        new_status=LeadStatus.CONTACTED,
        note=note,
    )


def mark_recommended(
    *,
    actor: User,
    lead: Lead,
    note: str = "",
    recommended_course_id: int | None = None,
) -> Lead:
    return transition_lead(
        actor=actor,
        lead=lead,
        new_status=LeadStatus.RECOMMENDED,
        note=note,
        recommended_course_id=recommended_course_id,
    )


def mark_quote_pending(*, actor: User, lead: Lead, note: str = "") -> Lead:
    return transition_lead(
        actor=actor,
        lead=lead,
        new_status=LeadStatus.QUOTE_PENDING,
        note=note,
    )


def mark_lost(*, actor: User, lead: Lead, note: str = "", lost_reason: str = "") -> Lead:
    return transition_lead(
        actor=actor,
        lead=lead,
        new_status=LeadStatus.LOST,
        note=note,
        lost_reason=lost_reason,
    )


def apply_lead_conversion(
    *,
    actor: User,
    lead: Lead,
    note: str = "",
    converted_student_id: int | None = None,
) -> Lead:
    """
    Apply converted status (no permission check).

    Used by staff convert endpoint and by student registration linkage.
    """
    if lead.status == LeadStatus.CONVERTED:
        raise LeadServiceError("Lead is already converted.", code="already_converted")

    if lead.status == LeadStatus.RECOMMENDED:
        lead.status = LeadStatus.QUOTE_PENDING

    if LeadStatus.CONVERTED not in ALLOWED_TRANSITIONS.get(lead.status, frozenset()):
        raise LeadServiceError(
            f"Cannot convert lead from status {lead.status}.",
            code="invalid_transition",
        )

    _append_note(lead, note or "Converted toward registration.", actor=actor)
    lead.status = LeadStatus.CONVERTED
    lead.converted_at = timezone.now()
    if converted_student_id is not None:
        lead.converted_student_id = converted_student_id
    lead.save()
    return lead


def convert_lead(
    *,
    actor: User,
    lead: Lead,
    note: str = "",
    converted_student_id: int | None = None,
) -> Lead:
    """Staff-facing convert — permission checked."""
    _require_manager(actor)
    return apply_lead_conversion(
        actor=actor,
        lead=lead,
        note=note,
        converted_student_id=converted_student_id,
    )