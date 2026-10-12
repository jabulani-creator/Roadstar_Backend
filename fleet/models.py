"""
Durable data for the `fleet` domain.

Owns: instructor ops profiles, vehicles, pickup zones / service rules.

Plain English:
- InstructorProfile = who can teach which class/transmission, and where.
- Vehicle = training car and whether it is free, in maintenance, or defected.
- PickupZone = approved pickup geography + travel buffer / fee rules.

Does NOT own: lesson bookings, payments, public marketing copy.
"""

from django.conf import settings
from django.db import models


class LicenceClassCapability(models.TextChoices):
    CLASS_B = "B", "Class B"
    CLASS_C1 = "C1", "Class D / C1"
    CLASS_C = "C", "Class C"
    OTHER = "other", "Other / specialised"


class TransmissionCapability(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTOMATIC = "automatic", "Automatic"
    BOTH = "both", "Manual and automatic"


class InstructorStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ON_LEAVE = "on_leave", "On leave"
    INACTIVE = "inactive", "Inactive"


class VehicleStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    MAINTENANCE = "maintenance", "Maintenance"
    DEFECT = "defect", "Defect / unroadworthy"
    INACTIVE = "inactive", "Inactive"


class InstructorProfile(models.Model):
    """
    Operational instructor record linked to a login user.

    Public trust-page fields may also live on User; this model owns
    scheduling eligibility.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_profile",
    )
    display_name = models.CharField(max_length=160)
    employee_code = models.CharField(max_length=32, blank=True)
    home_branch = models.ForeignKey(
        "catalogue.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="instructors",
    )
    licence_classes = models.CharField(
        max_length=64,
        default="B",
        help_text="Comma-separated codes, e.g. B,C1",
    )
    transmission = models.CharField(
        max_length=16,
        choices=TransmissionCapability.choices,
        default=TransmissionCapability.BOTH,
    )
    credentials_note = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=16,
        choices=InstructorStatus.choices,
        default=InstructorStatus.ACTIVE,
    )
    show_on_public_page = models.BooleanField(
        default=False,
        help_text="If true, may appear on public instructors page.",
    )
    photo = models.ImageField(
        upload_to="fleet/instructors/",
        blank=True,
        help_text="Public profile photo. Leave blank to show the placeholder.",
    )
    photo_focus = models.CharField(
        max_length=16,
        choices=[
            ("center", "Center — full face in frame"),
            ("top", "Top — prefer upper body / standing shots"),
            ("bottom", "Bottom — prefer lower framing"),
        ],
        default="center",
        help_text="How the public card crops the photo.",
    )
    public_bio = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Internal staff notes.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name

    def licence_class_list(self) -> list[str]:
        return [c.strip() for c in self.licence_classes.split(",") if c.strip()]

    def can_teach(self, *, licence_class: str, transmission: str) -> bool:
        if self.status != InstructorStatus.ACTIVE:
            return False
        if licence_class and licence_class not in self.licence_class_list():
            return False
        if transmission:
            if self.transmission == TransmissionCapability.BOTH:
                return True
            return self.transmission == transmission
        return True


class VehicleType(models.TextChoices):
    PASSENGER = "passenger", "Passenger car"
    LIGHT_COMMERCIAL = "light_commercial", "Light commercial"
    HEAVY = "heavy", "Heavy vehicle"
    OTHER = "other", "Other"


class Vehicle(models.Model):
    """Training vehicle that can be assigned to lessons."""

    name = models.CharField(max_length=120, help_text="Friendly label, e.g. Corolla 1.")
    registration_number = models.CharField(max_length=32, unique=True)
    make_model = models.CharField(
        max_length=160,
        blank=True,
        help_text="Public make/model, e.g. Toyota Corolla.",
    )
    vehicle_type = models.CharField(
        max_length=32,
        choices=VehicleType.choices,
        default=VehicleType.PASSENGER,
    )
    public_description = models.TextField(
        blank=True,
        help_text="Short public note about its role in training.",
    )
    photo = models.ImageField(
        upload_to="fleet/vehicles/",
        blank=True,
        help_text=(
            "Public cutout photo (transparent PNG preferred). "
            "Leave blank to show the icon placeholder."
        ),
    )
    show_on_public_page = models.BooleanField(
        default=False,
        help_text="If true, may appear on the public fleet page.",
    )
    branch = models.ForeignKey(
        "catalogue.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vehicles",
    )
    licence_class = models.CharField(
        max_length=16,
        choices=LicenceClassCapability.choices,
        default=LicenceClassCapability.CLASS_B,
    )
    transmission = models.CharField(
        max_length=16,
        choices=TransmissionCapability.choices,
        default=TransmissionCapability.MANUAL,
    )
    status = models.CharField(
        max_length=16,
        choices=VehicleStatus.choices,
        default=VehicleStatus.AVAILABLE,
    )
    status_note = models.CharField(
        max_length=255,
        blank=True,
        help_text="Why it is in maintenance/defect, if applicable.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.registration_number})"

    @property
    def is_assignable(self) -> bool:
        return self.status == VehicleStatus.AVAILABLE

    def matches(self, *, licence_class: str, transmission: str) -> bool:
        if licence_class and self.licence_class != licence_class:
            return False
        if transmission:
            if self.transmission == TransmissionCapability.BOTH:
                return True
            return self.transmission == transmission
        return True


class PickupZone(models.Model):
    """
    Approved pickup geography and travel rules for a branch.
    """

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=140)
    branch = models.ForeignKey(
        "catalogue.Branch",
        on_delete=models.CASCADE,
        related_name="pickup_zones",
    )
    description = models.TextField(blank=True)
    radius_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Approved service radius from branch / zone centre.",
    )
    travel_buffer_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Minutes to reserve for travel before/after a pickup lesson.",
    )
    travel_fee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional disclosed travel fee.",
    )
    currency = models.CharField(max_length=8, default="ZMW")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["branch__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.branch})"
