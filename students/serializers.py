"""API input/output shapes for `students`."""

from rest_framework import serializers

from .models import ConsentRecord, ConsentType, Student


class ConsentRecordSerializer(serializers.ModelSerializer):
    consent_type_label = serializers.CharField(
        source="get_consent_type_display",
        read_only=True,
    )

    class Meta:
        model = ConsentRecord
        fields = (
            "id",
            "consent_type",
            "consent_type_label",
            "accepted",
            "accepted_at",
            "notes",
            "created_at",
        )
        read_only_fields = fields


class StudentRegisterSerializer(serializers.Serializer):
    """Public registration payload."""

    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=160)
    phone = serializers.CharField(max_length=32)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    selected_course = serializers.IntegerField(required=False, allow_null=True)
    preferred_branch = serializers.IntegerField(required=False, allow_null=True)
    preferred_schedule = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    pickup_notes = serializers.CharField(required=False, allow_blank=True, default="")
    sponsor_name = serializers.CharField(required=False, allow_blank=True, default="")
    sponsor_phone = serializers.CharField(required=False, allow_blank=True, default="")
    sponsor_email = serializers.EmailField(required=False, allow_blank=True, default="")
    sponsor_relationship = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    referral_source = serializers.CharField(required=False, allow_blank=True, default="")
    referral_detail = serializers.CharField(required=False, allow_blank=True, default="")
    source_lead = serializers.IntegerField(required=False, allow_null=True)

    # Consents — terms + privacy required; marketing optional.
    accept_terms = serializers.BooleanField()
    accept_privacy = serializers.BooleanField()
    accept_marketing = serializers.BooleanField(required=False, default=False)


class StudentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    checklist_status_label = serializers.CharField(
        source="get_checklist_status_display",
        read_only=True,
    )
    selected_course_name = serializers.CharField(
        source="selected_course.name",
        read_only=True,
        allow_null=True,
    )
    preferred_branch_name = serializers.CharField(
        source="preferred_branch.name",
        read_only=True,
        allow_null=True,
    )
    consents = ConsentRecordSerializer(many=True, read_only=True)
    has_accepted_terms = serializers.SerializerMethodField()
    has_accepted_privacy = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            "id",
            "user",
            "full_name",
            "phone",
            "email",
            "date_of_birth",
            "national_id",
            "selected_course",
            "selected_course_name",
            "preferred_branch",
            "preferred_branch_name",
            "preferred_schedule",
            "pickup_notes",
            "sponsor_name",
            "sponsor_phone",
            "sponsor_email",
            "sponsor_relationship",
            "referral_source",
            "referral_detail",
            "source_lead",
            "status",
            "status_label",
            "checklist_status",
            "checklist_status_label",
            "has_nrc_copy",
            "has_medical_form",
            "has_photos",
            "has_proof_of_payment",
            "internal_notes",
            "consents",
            "has_accepted_terms",
            "has_accepted_privacy",
            "registered_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status_label",
            "checklist_status_label",
            "selected_course_name",
            "preferred_branch_name",
            "source_lead",
            "consents",
            "has_accepted_terms",
            "has_accepted_privacy",
            "registered_at",
            "updated_at",
        )

    def get_has_accepted_terms(self, obj: Student) -> bool:
        return obj.consents.filter(
            consent_type=ConsentType.TERMS, accepted=True
        ).exists()

    def get_has_accepted_privacy(self, obj: Student) -> bool:
        return obj.consents.filter(
            consent_type=ConsentType.PRIVACY, accepted=True
        ).exists()


class StudentPortalSerializer(serializers.ModelSerializer):
    """Student-safe shape — no internal staff notes."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    selected_course_name = serializers.CharField(
        source="selected_course.name",
        read_only=True,
        allow_null=True,
    )
    preferred_branch_name = serializers.CharField(
        source="preferred_branch.name",
        read_only=True,
        allow_null=True,
    )
    consents = ConsentRecordSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "full_name",
            "phone",
            "email",
            "date_of_birth",
            "selected_course",
            "selected_course_name",
            "preferred_branch",
            "preferred_branch_name",
            "preferred_schedule",
            "pickup_notes",
            "sponsor_name",
            "sponsor_phone",
            "sponsor_email",
            "sponsor_relationship",
            "status",
            "status_label",
            "checklist_status",
            "consents",
            "registered_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "selected_course",
            "selected_course_name",
            "status",
            "status_label",
            "checklist_status",
            "consents",
            "registered_at",
            "updated_at",
        )


class StudentStatusSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
