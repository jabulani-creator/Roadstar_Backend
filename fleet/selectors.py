"""Read queries for fleet — public instructors opt-in; ops lists for staff/scheduler."""

from __future__ import annotations

from django.db.models import QuerySet

from .models import (
    InstructorProfile,
    InstructorStatus,
    PickupZone,
    TransmissionCapability,
    Vehicle,
    VehicleStatus,
)


def instructors_public() -> QuerySet[InstructorProfile]:
    return (
        InstructorProfile.objects.select_related("user", "home_branch")
        .filter(
            show_on_public_page=True,
            status=InstructorStatus.ACTIVE,
        )
        .order_by("display_name")
    )


def instructors_staff(*, status: str | None = None) -> QuerySet[InstructorProfile]:
    qs = InstructorProfile.objects.select_related("user", "home_branch").all()
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("display_name")


def instructor_by_id(*, instructor_id: int) -> InstructorProfile | None:
    return (
        InstructorProfile.objects.select_related("user", "home_branch")
        .filter(pk=instructor_id)
        .first()
    )


def eligible_instructors(
    *,
    licence_class: str,
    transmission: str,
    branch_id: int | None = None,
) -> QuerySet[InstructorProfile]:
    qs = instructors_staff(status=InstructorStatus.ACTIVE)
    if branch_id is not None:
        qs = qs.filter(home_branch_id=branch_id)
    # Filter in Python for comma-separated licence_classes + BOTH transmission.
    ids = [
        p.id
        for p in qs
        if p.can_teach(licence_class=licence_class, transmission=transmission)
    ]
    return InstructorProfile.objects.select_related("user", "home_branch").filter(
        id__in=ids
    ).order_by("display_name")


def vehicles_public() -> QuerySet[Vehicle]:
    """
    Vehicles opted into the public fleet page.

    Only available vehicles — maintenance/defect must not appear publicly
    (creates doubt for prospects). Staff still see full status lists.
    """
    return (
        Vehicle.objects.select_related("branch")
        .filter(
            show_on_public_page=True,
            status=VehicleStatus.AVAILABLE,
        )
        .order_by("licence_class", "name")
    )


def vehicles_staff(*, status: str | None = None) -> QuerySet[Vehicle]:
    qs = Vehicle.objects.select_related("branch").all()
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("name")


def vehicle_by_id(*, vehicle_id: int) -> Vehicle | None:
    return Vehicle.objects.select_related("branch").filter(pk=vehicle_id).first()


def eligible_vehicles(
    *,
    licence_class: str,
    transmission: str,
    branch_id: int | None = None,
) -> QuerySet[Vehicle]:
    qs = Vehicle.objects.select_related("branch").filter(status=VehicleStatus.AVAILABLE)
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)
    if licence_class:
        qs = qs.filter(licence_class=licence_class)
    if transmission:
        qs = qs.filter(
            transmission__in=[transmission, TransmissionCapability.BOTH]
        )
    return qs.order_by("name")


def pickup_zones_staff(*, branch_id: int | None = None, active_only: bool = False) -> QuerySet[PickupZone]:
    qs = PickupZone.objects.select_related("branch").all()
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("branch__name", "name")


def pickup_zone_by_id(*, zone_id: int) -> PickupZone | None:
    return PickupZone.objects.select_related("branch").filter(pk=zone_id).first()


def pickup_zone_by_slug(*, slug: str) -> PickupZone | None:
    return PickupZone.objects.select_related("branch").filter(slug=slug).first()
