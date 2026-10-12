"""API input/output shapes for `scheduler`."""

from rest_framework import serializers

from .models import LessonBooking, LessonCompletion


class ConflictCheckSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    instructor = serializers.IntegerField()
    vehicle = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(required=False, default=60)
    travel_buffer_minutes = serializers.IntegerField(required=False, default=0)
    exclude_booking_id = serializers.IntegerField(required=False, allow_null=True)


class BookingCreateSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    instructor = serializers.IntegerField()
    vehicle = serializers.IntegerField()
    course = serializers.IntegerField(required=False, allow_null=True)
    entitlement_account = serializers.IntegerField(required=False, allow_null=True)
    branch = serializers.IntegerField(required=False, allow_null=True)
    pickup_zone = serializers.IntegerField(required=False, allow_null=True)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(required=False)
    travel_buffer_minutes = serializers.IntegerField(required=False, default=0)
    internal_notes = serializers.CharField(required=False, allow_blank=True, default="")


class LessonCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonCompletion
        fields = (
            "id",
            "checked_in_at",
            "checked_out_at",
            "actual_duration_minutes",
            "attended",
            "no_show",
            "skills_notes",
            "instructor_notes",
            "incident_flag",
            "vehicle_defect_flag",
            "credits_to_deduct",
            "credits_deducted",
            "deduction_note",
            "created_at",
        )
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    instructor_name = serializers.CharField(
        source="instructor.display_name", read_only=True
    )
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True)
    course_name = serializers.CharField(
        source="course.name", read_only=True, allow_null=True
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True, allow_null=True
    )
    pickup_zone_name = serializers.CharField(
        source="pickup_zone.name", read_only=True, allow_null=True
    )
    completion = serializers.SerializerMethodField()

    class Meta:
        model = LessonBooking
        fields = (
            "id",
            "student",
            "student_name",
            "course",
            "course_name",
            "entitlement_account",
            "instructor",
            "instructor_name",
            "vehicle",
            "vehicle_name",
            "branch",
            "branch_name",
            "pickup_zone",
            "pickup_zone_name",
            "starts_at",
            "ends_at",
            "duration_minutes",
            "travel_buffer_minutes",
            "status",
            "status_label",
            "internal_notes",
            "controller_feedback",
            "conflict_warnings",
            "override_note",
            "confirmed_at",
            "cancelled_at",
            "cancel_reason",
            "completion",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "student_name",
            "course_name",
            "instructor_name",
            "vehicle_name",
            "branch_name",
            "pickup_zone_name",
            "status",
            "status_label",
            "controller_feedback",
            "conflict_warnings",
            "override_note",
            "confirmed_at",
            "cancelled_at",
            "cancel_reason",
            "completion",
            "created_at",
            "updated_at",
        )

    def get_completion(self, obj: LessonBooking):
        try:
            return LessonCompletionSerializer(obj.completion).data
        except LessonCompletion.DoesNotExist:
            return None


class BookingPortalSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(
        source="instructor.display_name", read_only=True
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True, allow_null=True
    )
    pickup_zone_name = serializers.CharField(
        source="pickup_zone.name", read_only=True, allow_null=True
    )

    class Meta:
        model = LessonBooking
        fields = (
            "id",
            "starts_at",
            "ends_at",
            "duration_minutes",
            "status",
            "instructor_name",
            "branch_name",
            "pickup_zone_name",
        )
        read_only_fields = fields


class ConfirmSerializer(serializers.Serializer):
    force_override = serializers.BooleanField(required=False, default=False)
    override_note = serializers.CharField(required=False, allow_blank=True, default="")


class FeedbackSerializer(serializers.Serializer):
    feedback = serializers.CharField(required=False, allow_blank=True, default="")


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CompleteLessonSerializer(serializers.Serializer):
    checked_in_at = serializers.DateTimeField(required=False, allow_null=True)
    checked_out_at = serializers.DateTimeField(required=False, allow_null=True)
    actual_duration_minutes = serializers.IntegerField(required=False, allow_null=True)
    attended = serializers.BooleanField(required=False, default=True)
    no_show = serializers.BooleanField(required=False, default=False)
    skills_notes = serializers.CharField(required=False, allow_blank=True, default="")
    instructor_notes = serializers.CharField(required=False, allow_blank=True, default="")
    incident_flag = serializers.BooleanField(required=False, default=False)
    vehicle_defect_flag = serializers.BooleanField(required=False, default=False)
    credits_to_deduct = serializers.IntegerField(required=False, allow_null=True)
    deduction_note = serializers.CharField(required=False, allow_blank=True, default="")
