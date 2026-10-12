"""API input/output shapes for `fleet`."""

from rest_framework import serializers

from .models import InstructorProfile, PickupZone, Vehicle


def _absolute_photo_url(photo, request) -> str:
    if not photo:
        return ""
    url = photo.url
    if request is not None:
        return request.build_absolute_uri(url)
    return url


class AbsolutePhotoMixin:
    """Expose uploaded photo as an absolute URL string for the frontend."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        data["photo"] = _absolute_photo_url(getattr(instance, "photo", None), request)
        return data


# Backwards-compatible alias
VehiclePhotoMixin = AbsolutePhotoMixin


class InstructorPublicSerializer(AbsolutePhotoMixin, serializers.ModelSerializer):
    branch_name = serializers.CharField(
        source="home_branch.name", read_only=True, allow_null=True
    )
    transmission_label = serializers.CharField(
        source="get_transmission_display", read_only=True
    )
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = InstructorProfile
        fields = (
            "id",
            "display_name",
            "branch_name",
            "licence_classes",
            "transmission",
            "transmission_label",
            "credentials_note",
            "public_bio",
            "photo",
            "photo_focus",
        )
        read_only_fields = fields


class InstructorSerializer(AbsolutePhotoMixin, serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    transmission_label = serializers.CharField(
        source="get_transmission_display", read_only=True
    )
    user_email = serializers.EmailField(source="user.email", read_only=True)
    branch_name = serializers.CharField(
        source="home_branch.name", read_only=True, allow_null=True
    )
    photo = serializers.ImageField(required=False, allow_null=True)
    clear_photo = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = InstructorProfile
        fields = (
            "id",
            "user",
            "user_email",
            "display_name",
            "employee_code",
            "home_branch",
            "branch_name",
            "licence_classes",
            "transmission",
            "transmission_label",
            "credentials_note",
            "status",
            "status_label",
            "show_on_public_page",
            "photo",
            "photo_focus",
            "clear_photo",
            "public_bio",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_email",
            "branch_name",
            "transmission_label",
            "status_label",
            "created_at",
            "updated_at",
        )


class InstructorCreateSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    display_name = serializers.CharField(required=False, allow_blank=True, default="")
    employee_code = serializers.CharField(required=False, allow_blank=True, default="")
    home_branch = serializers.IntegerField(required=False, allow_null=True)
    licence_classes = serializers.CharField(required=False, default="B")
    transmission = serializers.CharField(required=False, default="both")
    credentials_note = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.CharField(required=False, default="active")
    show_on_public_page = serializers.BooleanField(required=False, default=False)
    public_bio = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class VehiclePublicSerializer(AbsolutePhotoMixin, serializers.ModelSerializer):
    """Public fleet card — no registration number."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    licence_class_label = serializers.CharField(
        source="get_licence_class_display", read_only=True
    )
    transmission_label = serializers.CharField(
        source="get_transmission_display", read_only=True
    )
    vehicle_type_label = serializers.CharField(
        source="get_vehicle_type_display", read_only=True
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True, allow_null=True
    )
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "name",
            "make_model",
            "vehicle_type",
            "vehicle_type_label",
            "licence_class",
            "licence_class_label",
            "transmission",
            "transmission_label",
            "branch_name",
            "status",
            "status_label",
            "public_description",
            "photo",
        )
        read_only_fields = fields


class VehicleSerializer(AbsolutePhotoMixin, serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    licence_class_label = serializers.CharField(
        source="get_licence_class_display", read_only=True
    )
    transmission_label = serializers.CharField(
        source="get_transmission_display", read_only=True
    )
    vehicle_type_label = serializers.CharField(
        source="get_vehicle_type_display", read_only=True
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True, allow_null=True
    )
    is_assignable = serializers.BooleanField(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    clear_photo = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "name",
            "registration_number",
            "make_model",
            "vehicle_type",
            "vehicle_type_label",
            "public_description",
            "photo",
            "clear_photo",
            "show_on_public_page",
            "branch",
            "branch_name",
            "licence_class",
            "licence_class_label",
            "transmission",
            "transmission_label",
            "status",
            "status_label",
            "status_note",
            "is_assignable",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "branch_name",
            "licence_class_label",
            "transmission_label",
            "vehicle_type_label",
            "status",
            "status_label",
            "status_note",
            "is_assignable",
            "created_at",
            "updated_at",
        )


class VehicleStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class PickupZoneSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = PickupZone
        fields = (
            "id",
            "name",
            "slug",
            "branch",
            "branch_name",
            "description",
            "radius_km",
            "travel_buffer_minutes",
            "travel_fee_amount",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "branch_name",
            "created_at",
            "updated_at",
        )
