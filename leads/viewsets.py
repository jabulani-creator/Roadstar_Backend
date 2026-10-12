"""
HTTP endpoints for `leads`.

Public may submit. Staff own the inbox. Business rules live in services.py.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from .permissions import IsLeadManager, IsLeadStaff
from .selectors import lead_by_id, lead_inbox_stats, leads_staff
from .serializers import (
    LeadAssignSerializer,
    LeadPublicCreatedSerializer,
    LeadPublicCreateSerializer,
    LeadSerializer,
    LeadStatusUpdateSerializer,
)
from .services import (
    LeadServiceError,
    assign_lead,
    convert_lead,
    create_lead,
    mark_contacted,
    mark_lost,
    mark_quote_pending,
    mark_recommended,
    update_lead,
)

User = get_user_model()


def _service_error(exc: LeadServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


class PublicLeadCreateView(RoadstarAPIView):
    """POST /api/v1/leads/ — prospect submits a structured enquiry."""

    permission_classes = [AllowAny]
    serializer_class = LeadPublicCreateSerializer

    def post(self, request: Request) -> Response:
        serializer = LeadPublicCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            lead = create_lead(data=serializer.validated_data)
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(
            LeadPublicCreatedSerializer(lead).data,
            status=status.HTTP_201_CREATED,
        )


class StaffLeadListView(RoadstarAPIView):
    """GET /api/v1/staff/leads/ — inbox list with optional filters."""

    permission_classes = [IsAuthenticated, IsLeadStaff]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        assigned = request.query_params.get("assigned_to")
        assigned_to_id = int(assigned) if assigned and assigned.isdigit() else None
        qs = leads_staff(status=status_filter, assigned_to_id=assigned_to_id)
        return Response(LeadSerializer(qs, many=True).data)


class StaffLeadStatsView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadStaff]

    def get(self, request: Request) -> Response:
        return Response(lead_inbox_stats())


class StaffLeadDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadStaff]

    def get(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeadSerializer(lead).data)

    def patch(self, request: Request, lead_id: int) -> Response:
        if not IsLeadManager().has_permission(request, self):
            return Response(
                {"detail": "Lead manager access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeadSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            lead = update_lead(
                actor=request.user,
                lead=lead,
                data=serializer.validated_data,
            )
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)


class StaffLeadAssignView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = LeadAssignSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        assignee_id = body.validated_data.get("assigned_to")
        assignee = None
        if assignee_id is not None:
            assignee = User.objects.filter(pk=assignee_id).first()
            if assignee is None:
                return Response(
                    {"detail": "Assignee not found.", "code": "assignee_not_found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            lead = assign_lead(actor=request.user, lead=lead, assigned_to=assignee)
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)


class StaffLeadContactedView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = LeadStatusUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            lead = mark_contacted(
                actor=request.user,
                lead=lead,
                note=body.validated_data.get("note", ""),
            )
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)


class StaffLeadRecommendedView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = LeadStatusUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            lead = mark_recommended(
                actor=request.user,
                lead=lead,
                note=body.validated_data.get("note", ""),
                recommended_course_id=body.validated_data.get("recommended_course"),
            )
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)


class StaffLeadQuotePendingView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = LeadStatusUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            lead = mark_quote_pending(
                actor=request.user,
                lead=lead,
                note=body.validated_data.get("note", ""),
            )
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)


class StaffLeadLostView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = LeadStatusUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            lead = mark_lost(
                actor=request.user,
                lead=lead,
                note=body.validated_data.get("note", ""),
                lost_reason=body.validated_data.get("lost_reason", ""),
            )
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)


class StaffLeadConvertView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLeadManager]

    def post(self, request: Request, lead_id: int) -> Response:
        lead = lead_by_id(lead_id=lead_id)
        if lead is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = LeadStatusUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            lead = convert_lead(
                actor=request.user,
                lead=lead,
                note=body.validated_data.get("note", ""),
                converted_student_id=body.validated_data.get("converted_student_id"),
            )
        except LeadServiceError as exc:
            return _service_error(exc)
        return Response(LeadSerializer(lead).data)
