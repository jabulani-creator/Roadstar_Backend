"""API input/output shapes for `leads`."""

from rest_framework import serializers

from .models import Lead


class LeadPublicCreateSerializer(serializers.ModelSerializer):
    """What a prospect may submit (no staff fields)."""

    class Meta:
        model = Lead
        fields = (
            "full_name",
            "phone",
            "email",
            "preferred_contact",
            "experience_level",
            "licence_class",
            "transmission",
            "preferred_branch",
            "preferred_schedule",
            "message",
            "interested_course",
            "channel",
            "referral_source",
            "referral_detail",
            "whatsapp_summary",
        )


class LeadPublicCreatedSerializer(serializers.ModelSerializer):
    """Minimal acknowledgement after public submit."""

    class Meta:
        model = Lead
        fields = ("id", "full_name", "status", "created_at")
        read_only_fields = fields


class LeadSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    referral_source_label = serializers.CharField(
        source="get_referral_source_display",
        read_only=True,
    )
    experience_level_label = serializers.CharField(
        source="get_experience_level_display",
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
    preferred_branch_name = serializers.CharField(
        source="preferred_branch.name",
        read_only=True,
        allow_null=True,
    )
    interested_course_name = serializers.CharField(
        source="interested_course.name",
        read_only=True,
        allow_null=True,
    )
    recommended_course_name = serializers.CharField(
        source="recommended_course.name",
        read_only=True,
        allow_null=True,
    )
    assigned_to_email = serializers.EmailField(
        source="assigned_to.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Lead
        fields = (
            "id",
            "full_name",
            "phone",
            "email",
            "preferred_contact",
            "experience_level",
            "experience_level_label",
            "licence_class",
            "licence_class_label",
            "transmission",
            "transmission_label",
            "preferred_branch",
            "preferred_branch_name",
            "preferred_schedule",
            "message",
            "interested_course",
            "interested_course_name",
            "recommended_course",
            "recommended_course_name",
            "channel",
            "channel_label",
            "referral_source",
            "referral_source_label",
            "referral_detail",
            "whatsapp_summary",
            "status",
            "status_label",
            "assigned_to",
            "assigned_to_email",
            "internal_notes",
            "lost_reason",
            "converted_at",
            "converted_student_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "status_label",
            "channel_label",
            "referral_source_label",
            "experience_level_label",
            "licence_class_label",
            "transmission_label",
            "preferred_branch_name",
            "interested_course_name",
            "recommended_course_name",
            "assigned_to_email",
            "converted_at",
            "converted_student_id",
            "created_at",
            "updated_at",
        )


class LeadStatusUpdateSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
    lost_reason = serializers.CharField(required=False, allow_blank=True, default="")
    recommended_course = serializers.IntegerField(required=False, allow_null=True)
    converted_student_id = serializers.IntegerField(required=False, allow_null=True)


class LeadAssignSerializer(serializers.Serializer):
    assigned_to = serializers.IntegerField(required=False, allow_null=True)
