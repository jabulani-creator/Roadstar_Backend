"""
Write workflows for `fleet`.

Plain English:
- Staff maintain instructor eligibility, vehicle status, and pickup zones.
- Vehicles in maintenance/defect cannot be treated as assignable.
- Eligibility queries power the future scheduler forms.
"""

from __future__ import annotations

from django.db import transaction
from django.utils.text import slugify

from accounts.models import StaffRole, StaffRoleAssignment, User
from accounts.permissions import user_has_any_role, user_is_staff_operator
from catalogue.models import Branch

from .models import (
    InstructorProfile,
    InstructorStatus,
    PickupZone,
    Vehicle,
    VehicleStatus,
)


class FleetServiceError(Exception):
    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _can_manage(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.RECEPTION],
        )
        or user.is_superuser
        or user.is_staff
    )


def _require_manager(actor: User) -> None:
    if not _can_manage(actor):
        raise FleetServiceError("Not allowed to manage fleet.", code="forbidden")


def _unique_slug(base: str, *, exclude_pk=None) -> str:
    base = slugify(base) or "pickup-zone"
    slug = base
    n = 2
    while True:
        qs = PickupZone.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return slug
        slug = f"{base}-{n}"
        n += 1


def _normalize_licence_classes(value: str) -> str:
    parts = [p.strip().upper() if p.strip().upper() != "OTHER" else "other" for p in value.split(",")]
    # Keep B/C1/C style; "other" stays lowercase to match choices.
    cleaned = []
    for p in parts:
        if not p:
            continue
        if p.lower() == "other":
            cleaned.append("other")
        else:
            cleaned.append(p)
    return ",".join(dict.fromkeys(cleaned))  # stable unique


@transaction.atomic
def create_instructor_profile(*, actor: User, data: dict) -> InstructorProfile:
    _require_manager(actor)
    payload = dict(data)
    user_id = payload.pop("user")
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        raise FleetServiceError("User not found.", code="user_not_found")
    if InstructorProfile.objects.filter(user=user).exists():
        raise FleetServiceError(
            "This user already has an instructor profile.",
            code="already_exists",
        )

    if "licence_classes" in payload:
        payload["licence_classes"] = _normalize_licence_classes(
            payload["licence_classes"]
        )

    home_branch = payload.pop("home_branch", None)
    if home_branch is not None and not isinstance(home_branch, Branch):
        branch = Branch.objects.filter(pk=home_branch).first()
        if branch is None:
            raise FleetServiceError("Branch not found.", code="branch_not_found")
        payload["home_branch"] = branch
    elif isinstance(home_branch, Branch):
        payload["home_branch"] = home_branch

    payload.setdefault(
        "display_name",
        (f"{user.first_name} {user.last_name}".strip() or user.email),
    )
    profile = InstructorProfile.objects.create(user=user, **payload)

    # Ensure they carry the instructor role badge for dashboard access.
    StaffRoleAssignment.objects.get_or_create(user=user, role=StaffRole.INSTRUCTOR)
    return profile


def update_instructor_profile(
    *, actor: User, profile: InstructorProfile, data: dict
) -> InstructorProfile:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("user", None)
    clear_photo = bool(payload.pop("clear_photo", False))
    if "licence_classes" in payload and payload["licence_classes"] is not None:
        payload["licence_classes"] = _normalize_licence_classes(
            payload["licence_classes"]
        )
    if "home_branch" in payload and payload["home_branch"] is not None:
        hb = payload["home_branch"]
        if not isinstance(hb, Branch):
            branch = Branch.objects.filter(pk=hb).first()
            if branch is None:
                raise FleetServiceError("Branch not found.", code="branch_not_found")
            payload["home_branch"] = branch
    if clear_photo:
        if profile.photo:
            profile.photo.delete(save=False)
        profile.photo = None
        payload.pop("photo", None)
    for field, value in payload.items():
        setattr(profile, field, value)
    profile.save()
    return profile


def create_vehicle(*, actor: User, data: dict) -> Vehicle:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("clear_photo", None)
    reg = (payload.get("registration_number") or "").strip().upper()
    if not reg:
        raise FleetServiceError(
            "Registration number is required.",
            code="invalid_registration",
        )
    if Vehicle.objects.filter(registration_number__iexact=reg).exists():
        raise FleetServiceError(
            "A vehicle with this registration already exists.",
            code="already_exists",
        )
    payload["registration_number"] = reg
    branch = payload.get("branch")
    if branch is not None and not isinstance(branch, Branch):
        resolved = Branch.objects.filter(pk=branch).first()
        if resolved is None:
            raise FleetServiceError("Branch not found.", code="branch_not_found")
        payload["branch"] = resolved
    payload.setdefault("status", VehicleStatus.AVAILABLE)
    return Vehicle.objects.create(**payload)


def update_vehicle(*, actor: User, vehicle: Vehicle, data: dict) -> Vehicle:
    _require_manager(actor)
    payload = dict(data)
    clear_photo = bool(payload.pop("clear_photo", False))
    if "registration_number" in payload and payload["registration_number"]:
        reg = payload["registration_number"].strip().upper()
        clash = (
            Vehicle.objects.filter(registration_number__iexact=reg)
            .exclude(pk=vehicle.pk)
            .exists()
        )
        if clash:
            raise FleetServiceError(
                "A vehicle with this registration already exists.",
                code="already_exists",
            )
        payload["registration_number"] = reg
    if clear_photo:
        if vehicle.photo:
            vehicle.photo.delete(save=False)
        vehicle.photo = None
        payload.pop("photo", None)
    for field, value in payload.items():
        setattr(vehicle, field, value)
    vehicle.save()
    return vehicle


def set_vehicle_status(
    *,
    actor: User,
    vehicle: Vehicle,
    status: str,
    note: str = "",
) -> Vehicle:
    _require_manager(actor)
    if status not in VehicleStatus.values:
        raise FleetServiceError("Unknown vehicle status.", code="invalid_status")
    if status in {VehicleStatus.MAINTENANCE, VehicleStatus.DEFECT} and not note.strip():
        raise FleetServiceError(
            "A note is required when marking maintenance or defect.",
            code="note_required",
        )
    vehicle.status = status
    if note.strip():
        vehicle.status_note = note.strip()
    elif status == VehicleStatus.AVAILABLE:
        vehicle.status_note = ""
    vehicle.save(update_fields=["status", "status_note", "updated_at"])
    return vehicle


def create_pickup_zone(*, actor: User, data: dict) -> PickupZone:
    _require_manager(actor)
    payload = dict(data)
    branch_id = payload.get("branch")
    if isinstance(branch_id, Branch):
        branch = branch_id
    else:
        branch = Branch.objects.filter(pk=branch_id).first()
    if branch is None:
        raise FleetServiceError("Branch not found.", code="branch_not_found")

    name = (payload.get("name") or "").strip()
    if not name:
        raise FleetServiceError("Name is required.", code="invalid_name")

    radius = payload.get("radius_km")
    if radius is None or radius <= 0:
        raise FleetServiceError(
            "radius_km must be greater than zero.",
            code="invalid_radius",
        )

    payload["branch"] = branch
    payload["name"] = name
    payload.setdefault("slug", _unique_slug(name))
    return PickupZone.objects.create(**payload)


def update_pickup_zone(*, actor: User, zone: PickupZone, data: dict) -> PickupZone:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("slug", None)
    if "radius_km" in payload and payload["radius_km"] is not None:
        if payload["radius_km"] <= 0:
            raise FleetServiceError(
                "radius_km must be greater than zero.",
                code="invalid_radius",
            )
    for field, value in payload.items():
        setattr(zone, field, value)
    zone.save()
    return zone


def assert_vehicle_assignable(vehicle: Vehicle) -> None:
    if not vehicle.is_assignable:
        raise FleetServiceError(
            f"Vehicle is not assignable (status={vehicle.status}).",
            code="vehicle_unavailable",
        )


def assert_instructor_eligible(
    profile: InstructorProfile,
    *,
    licence_class: str,
    transmission: str,
) -> None:
    if profile.status != InstructorStatus.ACTIVE:
        raise FleetServiceError(
            f"Instructor is not active (status={profile.status}).",
            code="instructor_unavailable",
        )
    if not profile.can_teach(licence_class=licence_class, transmission=transmission):
        raise FleetServiceError(
            "Instructor is not eligible for this class/transmission.",
            code="instructor_ineligible",
        )


def assert_pickup_zone_active(zone: PickupZone) -> None:
    if not zone.is_active:
        raise FleetServiceError(
            "Pickup zone is inactive.",
            code="pickup_zone_inactive",
        )
