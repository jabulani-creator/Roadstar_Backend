"""
API input/output shapes for `catalogue`.

Plain English:
- Decide which branch/course/promotion fields become JSON.
- Do not approve courses here — that belongs in services later.
"""

from rest_framework import serializers

from .models import Branch, Course, Promotion


class BranchSerializer(serializers.ModelSerializer):
    """Public/staff branch location card."""

    class Meta:
        model = Branch
        fields = (
            "id",
            "name",
            "slug",
            "address",
            "landmark",
            "map_url",
            "latitude",
            "longitude",
            "operating_hours",
            "primary_phone",
            "secondary_phone",
            "email",
            "classes_available_note",
            "is_active",
        )
        read_only_fields = ("id", "slug")


class BranchSummarySerializer(serializers.ModelSerializer):
    """Small branch chip used inside course payloads."""

    class Meta:
        model = Branch
        fields = ("id", "name", "slug")
        read_only_fields = fields


class CourseSerializer(serializers.ModelSerializer):
    """
    Course card / detail shape.

    `branches` is writable by id list for staff create/update later.
    Nested `branch_details` is read-only for nicer public responses.
    """

    branch_details = BranchSummarySerializer(
        source="branches",
        many=True,
        read_only=True,
    )
    licence_class_label = serializers.CharField(
        source="get_licence_class_display",
        read_only=True,
    )
    transmission_label = serializers.CharField(
        source="get_transmission_display",
        read_only=True,
    )
    level_label = serializers.CharField(
        source="get_level_display",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    is_public = serializers.BooleanField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "description",
            "licence_class",
            "licence_class_label",
            "transmission",
            "transmission_label",
            "level",
            "level_label",
            "duration_days",
            "min_age",
            "max_gvm_kg",
            "lesson_count",
            "lesson_unit_minutes",
            "price_amount",
            "currency",
            "show_price",
            "inclusions",
            "exclusions",
            "status",
            "status_label",
            "is_public",
            "price_updated_at",
            "branches",
            "branch_details",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "approved_at",
            "created_at",
            "updated_at",
            "licence_class_label",
            "transmission_label",
            "level_label",
            "status_label",
            "is_public",
            "branch_details",
        )


class CoursePublicSerializer(CourseSerializer):
    """
    Public catalogue shape.

    Staff-only workflow fields stay out of public responses.
    """

    class Meta(CourseSerializer.Meta):
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "description",
            "licence_class",
            "licence_class_label",
            "transmission",
            "transmission_label",
            "level",
            "level_label",
            "duration_days",
            "min_age",
            "max_gvm_kg",
            "lesson_count",
            "lesson_unit_minutes",
            "price_amount",
            "currency",
            "show_price",
            "inclusions",
            "exclusions",
            "price_updated_at",
            "branch_details",
        )
        read_only_fields = fields


class PromotionSerializer(serializers.ModelSerializer):
    """Promotion payload for staff and public (when active)."""

    is_currently_active = serializers.BooleanField(read_only=True)
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    course_details = CoursePublicSerializer(
        source="courses",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Promotion
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "terms",
            "discount_label",
            "courses",
            "course_details",
            "starts_at",
            "ends_at",
            "status",
            "status_label",
            "is_currently_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
            "status_label",
            "is_currently_active",
            "course_details",
        )


class PromotionPublicSerializer(serializers.ModelSerializer):
    """Public promotion card — only currently meaningful fields."""

    is_currently_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Promotion
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "terms",
            "discount_label",
            "starts_at",
            "ends_at",
            "is_currently_active",
        )
        read_only_fields = fields


class CourseStatusSerializer(serializers.Serializer):
    """Tiny body for approve/reject actions later."""

    note = serializers.CharField(required=False, allow_blank=True, default="")
