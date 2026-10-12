"""
API input/output shapes for `accounts`.

Plain English:
- Serializers decide which user fields become JSON for the frontend.
- They do NOT decide who is allowed to do what (that is permissions/services).
- Never include password hashes in API output.
"""

from rest_framework import serializers

from .models import StaffRoleAssignment, User


class StaffRoleAssignmentSerializer(serializers.ModelSerializer):
    """
    One job badge on a user.

    Example JSON:
    {"role": "owner", "role_label": "Owner / Admin"}
    """

    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = StaffRoleAssignment
        fields = ("role", "role_label")
        read_only_fields = fields


class UserMeSerializer(serializers.ModelSerializer):
    """
    Shape returned by GET /api/v1/auth/me/.

    The frontend uses this to show the right dashboard links.
    Backend permissions still enforce every sensitive action.
    """

    roles = StaffRoleAssignmentSerializer(
        source="role_assignments",
        many=True,
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "is_staff",
            "is_superuser",
            "roles",
        )
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    """Input for logged-in password change."""

    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Input for requesting a reset email."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Input for completing reset from email link."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class PublicStaffSerializer(serializers.ModelSerializer):
    """
    Safe public staff/instructor card.

    Deliberately omits email, phone, and permission flags.
    """

    roles = StaffRoleAssignmentSerializer(
        source="role_assignments",
        many=True,
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "public_title",
            "public_bio",
            "public_list_order",
            "roles",
        )
        read_only_fields = fields
