"""
HTTP endpoints for `scheduler`.

Staff booking lifecycle + conflict preview + portal upcoming lessons.
"""

from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from students.selectors import student_for_user

from .permissions import IsSchedulerController, IsSchedulerStaff
from .selectors import (
    booking_by_id,
    bookings_staff,
    instructor_daily_view,
    upcoming_for_student,
)
from .serializers import (
    BookingCreateSerializer,
    BookingPortalSerializer,
    BookingSerializer,
    CancelSerializer,
    CompleteLessonSerializer,
    ConfirmSerializer,
    ConflictCheckSerializer,
    FeedbackSerializer,
    LessonCompletionSerializer,
)
from .services import (
    SchedulerServiceError,
    cancel_booking,
    complete_lesson,
    confirm_booking,
    create_schedule_request,
    preview_conflicts,
    reject_booking,
    request_booking_changes,
    update_booking,
)


def _service_error(exc: SchedulerServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    body = {"detail": exc.message, "code": exc.code}
    if exc.conflicts:
        body["conflicts"] = exc.conflicts
    return Response(body, status=http_status)


class StaffConflictCheckView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerStaff]

    def post(self, request: Request) -> Response:
        serializer = ConflictCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conflicts = preview_conflicts(
                actor=request.user, data=serializer.validated_data
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response({"conflicts": conflicts, "has_conflicts": bool(conflicts)})


class StaffBookingListCreateView(RoadstarAPIView):
    def get_permissions(self):
        return [IsAuthenticated(), IsSchedulerStaff()]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        instructor = request.query_params.get("instructor")
        student = request.query_params.get("student")
        qs = bookings_staff(
            status=status_filter,
            instructor_id=int(instructor) if instructor and instructor.isdigit() else None,
            student_id=int(student) if student and student.isdigit() else None,
        )
        return Response(BookingSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = create_schedule_request(
                actor=request.user, data=serializer.validated_data
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class StaffBookingDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerStaff]

    def get(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookingSerializer(booking).data)

    def patch(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            booking = update_booking(
                actor=request.user,
                booking=booking,
                data=serializer.validated_data,
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response(BookingSerializer(booking).data)


class StaffBookingConfirmView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerController]

    def post(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = ConfirmSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            booking = confirm_booking(
                actor=request.user,
                booking=booking,
                force_override=body.validated_data.get("force_override", False),
                override_note=body.validated_data.get("override_note", ""),
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response(BookingSerializer(booking).data)


class StaffBookingRejectView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerController]

    def post(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = FeedbackSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            booking = reject_booking(
                actor=request.user,
                booking=booking,
                feedback=body.validated_data.get("feedback", ""),
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response(BookingSerializer(booking).data)


class StaffBookingRequestChangesView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerController]

    def post(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = FeedbackSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            booking = request_booking_changes(
                actor=request.user,
                booking=booking,
                feedback=body.validated_data.get("feedback", ""),
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response(BookingSerializer(booking).data)


class StaffBookingCancelView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerController]

    def post(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = CancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            booking = cancel_booking(
                actor=request.user,
                booking=booking,
                reason=body.validated_data.get("reason", ""),
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        return Response(BookingSerializer(booking).data)


class StaffBookingCompleteView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerStaff]

    def post(self, request: Request, booking_id: int) -> Response:
        booking = booking_by_id(booking_id=booking_id)
        if booking is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = CompleteLessonSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            completion = complete_lesson(
                actor=request.user,
                booking=booking,
                data=body.validated_data,
            )
        except SchedulerServiceError as exc:
            return _service_error(exc)
        booking = booking_by_id(booking_id=booking_id)
        return Response(
            {
                "booking": BookingSerializer(booking).data,
                "completion": LessonCompletionSerializer(completion).data,
            }
        )


class StaffInstructorDailyView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsSchedulerStaff]

    def get(self, request: Request, instructor_id: int) -> Response:
        day_raw = request.query_params.get("date")
        day = date.fromisoformat(day_raw) if day_raw else None
        qs = instructor_daily_view(instructor_id=instructor_id, day=day)
        return Response(BookingSerializer(qs, many=True).data)


class PortalUpcomingLessonsView(RoadstarAPIView):
    """GET /api/v1/scheduler/me/upcoming/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = upcoming_for_student(student=student)
        return Response(BookingPortalSerializer(qs, many=True).data)
