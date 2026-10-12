"""
HTTP endpoints for `students`.

Public register + portal me + staff management.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from leads.selectors import lead_by_id

from .permissions import IsStudentManager, IsStudentStaff
from .selectors import student_by_id, student_for_user, students_staff
from .serializers import (
    StudentPortalSerializer,
    StudentRegisterSerializer,
    StudentSerializer,
    StudentStatusSerializer,
)
from .services import (
    StudentServiceError,
    create_student_from_lead,
    register_student,
    set_student_status,
    update_student_portal,
    update_student_staff,
)
from .models import StudentStatus


def _service_error(exc: StudentServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


class PublicStudentRegisterView(RoadstarAPIView):
    """POST /api/v1/students/register/"""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = StudentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            student = register_student(data=serializer.validated_data)
        except StudentServiceError as exc:
            return _service_error(exc)
        return Response(
            StudentPortalSerializer(student).data,
            status=status.HTTP_201_CREATED,
        )


class StudentMeView(RoadstarAPIView):
    """GET/PATCH /api/v1/students/me/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(StudentPortalSerializer(student).data)

    def patch(self, request: Request) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = StudentPortalSerializer(student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            student = update_student_portal(
                user=request.user,
                student=student,
                data=serializer.validated_data,
            )
        except StudentServiceError as exc:
            return _service_error(exc)
        return Response(StudentPortalSerializer(student).data)


class StaffStudentListView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsStudentStaff]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        course = request.query_params.get("course")
        course_id = int(course) if course and course.isdigit() else None
        qs = students_staff(status=status_filter, course_id=course_id)
        return Response(StudentSerializer(qs, many=True).data)


class StaffStudentDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsStudentStaff]

    def get(self, request: Request, student_id: int) -> Response:
        student = student_by_id(student_id=student_id)
        if student is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StudentSerializer(student).data)

    def patch(self, request: Request, student_id: int) -> Response:
        if not IsStudentManager().has_permission(request, self):
            return Response(
                {"detail": "Student manager access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        student = student_by_id(student_id=student_id)
        if student is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StudentSerializer(student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            student = update_student_staff(
                actor=request.user,
                student=student,
                data=serializer.validated_data,
            )
        except StudentServiceError as exc:
            return _service_error(exc)
        return Response(StudentSerializer(student).data)


class StaffStudentActivateView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsStudentManager]

    def post(self, request: Request, student_id: int) -> Response:
        return self._set(request, student_id, StudentStatus.ACTIVE)

    def _set(self, request: Request, student_id: int, new_status: str) -> Response:
        student = student_by_id(student_id=student_id)
        if student is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = StudentStatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            student = set_student_status(
                actor=request.user,
                student=student,
                new_status=new_status,
                note=body.validated_data.get("note", ""),
            )
        except StudentServiceError as exc:
            return _service_error(exc)
        return Response(StudentSerializer(student).data)


class StaffStudentWithdrawView(StaffStudentActivateView):
    def post(self, request: Request, student_id: int) -> Response:
        return self._set(request, student_id, StudentStatus.WITHDRAWN)


class StaffStudentFromLeadView(RoadstarAPIView):
    """POST /api/v1/staff/students/from-lead/{lead_id}/"""

    permission_classes = [IsAuthenticated, IsStudentManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
        password = request.data.get("password")
        try:
            student = create_student_from_lead(
                actor=request.user,
                lead=lead,
                password=password,
            )
        except StudentServiceError as exc:
            return _service_error(exc)
        return Response(StudentSerializer(student).data, status=status.HTTP_201_CREATED)
