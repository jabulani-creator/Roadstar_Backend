"""
Write workflows for `accounts`.

Plain English:
- Password changes and resets happen here, not in views.
- Views only receive input, call these functions, and return results.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


class AccountsServiceError(Exception):
    """Domain error with a safe message for API clients."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


def change_password(*, user: User, current_password: str, new_password: str) -> None:
    """
    Change password for a logged-in user.

    Rules:
    - Current password must be correct.
    - New password must pass Django's password validators.
    """
    if not user.check_password(current_password):
        raise AccountsServiceError(
            "Current password is incorrect.",
            code="invalid_current_password",
        )

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise AccountsServiceError(
            " ".join(exc.messages),
            code="invalid_new_password",
        ) from exc

    user.set_password(new_password)
    user.save(update_fields=["password"])


def request_password_reset(*, email: str) -> None:
    """
    Start password reset for an email address.

    Security rule:
    - Always behave the same whether the email exists or not.
    - Never reveal to the client if the account was found.
    - Email is sent only when a matching active user exists.
    """
    normalized = User.objects.normalize_email(email)
    user = User.objects.filter(email__iexact=normalized, is_active=True).first()
    if user is None:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    reset_link = f"{frontend_base}/reset-password?uid={uid}&token={token}"

    send_mail(
        subject="Reset your Roadstar password",
        message=(
            "You requested a password reset for your Roadstar account.\n\n"
            f"Open this link to choose a new password:\n{reset_link}\n\n"
            "If you did not request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def confirm_password_reset(*, uid: str, token: str, new_password: str) -> None:
    """
    Complete password reset with uid + token from the email link.
    """
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id, is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise AccountsServiceError(
            "Invalid or expired reset link.",
            code="invalid_reset_link",
        ) from exc

    if not default_token_generator.check_token(user, token):
        raise AccountsServiceError(
            "Invalid or expired reset link.",
            code="invalid_reset_link",
        )

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise AccountsServiceError(
            " ".join(exc.messages),
            code="invalid_new_password",
        ) from exc

    user.set_password(new_password)
    user.save(update_fields=["password"])
