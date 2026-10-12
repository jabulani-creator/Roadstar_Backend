"""
HTTP endpoints for `catalogue`.

Public reads + staff management. Business rules live in services.py.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from .models import Branch, Course, Promotion
from .permissions import IsBranchManager, IsCatalogueEditor, IsCatalogueStaff
from .selectors import (
    get_branch_by_slug,
    get_branch_queryset,
    get_course_by_slug,
    get_promotion_by_slug,
    get_public_branches,
    get_public_courses,
    get_public_promotions,
    get_staff_courses,
    get_staff_promotions,
)
from .serializers import (
    BranchSerializer,
    CoursePublicSerializer,
    CourseSerializer,
    CourseStatusSerializer,
    PromotionPublicSerializer,
    PromotionSerializer,
)
from .services import (
    CatalogueServiceError,
    approve_course,
    approve_promotion,
    create_branch,
    create_course,
    create_promotion,
    deactivate_course,
    reject_course,
    reject_promotion,
    submit_course_for_review,
    update_branch,
    update_course,
    update_promotion,
)


def _service_error(exc: CatalogueServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


# --- Public ---


class PublicBranchListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = BranchSerializer(get_public_branches(), many=True).data
        return Response(data)


class PublicBranchDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        branch = get_branch_by_slug(slug, public_only=True)
        if branch is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BranchSerializer(branch).data)


class PublicCourseListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = CoursePublicSerializer(get_public_courses(), many=True).data
        return Response(data)


class PublicCourseDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        course = get_course_by_slug(slug, public_only=True)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CoursePublicSerializer(course).data)


class PublicPromotionListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = PromotionPublicSerializer(get_public_promotions(), many=True).data
        return Response(data)


# --- Staff: branches ---


class StaffBranchListCreateView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsBranchManager]

    def get(self, request: Request) -> Response:
        data = BranchSerializer(get_branch_queryset(), many=True).data
        return Response(data)

    def post(self, request: Request) -> Response:
        serializer = BranchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            branch = create_branch(actor=request.user, data=serializer.validated_data)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(BranchSerializer(branch).data, status=status.HTTP_201_CREATED)


class StaffBranchDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsBranchManager]

    def get_object(self, slug: str) -> Branch | None:
        return get_branch_by_slug(slug, public_only=False)

    def get(self, request: Request, slug: str) -> Response:
        branch = self.get_object(slug)
        if branch is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BranchSerializer(branch).data)

    def patch(self, request: Request, slug: str) -> Response:
        branch = self.get_object(slug)
        if branch is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BranchSerializer(branch, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            branch = update_branch(
                actor=request.user,
                branch=branch,
                data=serializer.validated_data,
            )
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(BranchSerializer(branch).data)


# --- Staff: courses ---


class StaffCourseListCreateView(RoadstarAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsCatalogueStaff()]
        return [IsAuthenticated(), IsCatalogueEditor()]

    def get(self, request: Request) -> Response:
        data = CourseSerializer(get_staff_courses(), many=True).data
        return Response(data)

    def post(self, request: Request) -> Response:
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            course = create_course(actor=request.user, data=serializer.validated_data)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)


class StaffCourseDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueStaff]

    def get_object(self, slug: str) -> Course | None:
        return get_course_by_slug(slug, public_only=False)

    def get(self, request: Request, slug: str) -> Response:
        course = self.get_object(slug)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CourseSerializer(course).data)

    def patch(self, request: Request, slug: str) -> Response:
        if not IsCatalogueEditor().has_permission(request, self):
            return Response({"detail": "Catalogue editor access required."}, status=status.HTTP_403_FORBIDDEN)
        course = self.get_object(slug)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CourseSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            course = update_course(
                actor=request.user,
                course=course,
                data=serializer.validated_data,
            )
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(CourseSerializer(course).data)


class StaffCourseSubmitView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def post(self, request: Request, slug: str) -> Response:
        course = get_course_by_slug(slug, public_only=False)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            course = submit_course_for_review(actor=request.user, course=course)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(CourseSerializer(course).data)


class StaffCourseApproveView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def post(self, request: Request, slug: str) -> Response:
        course = get_course_by_slug(slug, public_only=False)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            course = approve_course(actor=request.user, course=course)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(CourseSerializer(course).data)


class StaffCourseRejectView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def post(self, request: Request, slug: str) -> Response:
        course = get_course_by_slug(slug, public_only=False)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = CourseStatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            course = reject_course(
                actor=request.user,
                course=course,
                note=body.validated_data.get("note", ""),
            )
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(CourseSerializer(course).data)


class StaffCourseDeactivateView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def post(self, request: Request, slug: str) -> Response:
        course = get_course_by_slug(slug, public_only=False)
        if course is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            course = deactivate_course(actor=request.user, course=course)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(CourseSerializer(course).data)


# --- Staff: promotions ---


class StaffPromotionListCreateView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def get(self, request: Request) -> Response:
        data = PromotionSerializer(get_staff_promotions(), many=True).data
        return Response(data)

    def post(self, request: Request) -> Response:
        serializer = PromotionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            promotion = create_promotion(
                actor=request.user,
                data=serializer.validated_data,
            )
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(PromotionSerializer(promotion).data, status=status.HTTP_201_CREATED)


class StaffPromotionDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueStaff]

    def get_object(self, slug: str) -> Promotion | None:
        return get_promotion_by_slug(slug, public_only=False)

    def get(self, request: Request, slug: str) -> Response:
        promotion = self.get_object(slug)
        if promotion is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PromotionSerializer(promotion).data)

    def patch(self, request: Request, slug: str) -> Response:
        if not IsCatalogueEditor().has_permission(request, self):
            return Response({"detail": "Catalogue editor access required."}, status=status.HTTP_403_FORBIDDEN)
        promotion = self.get_object(slug)
        if promotion is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PromotionSerializer(promotion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            promotion = update_promotion(
                actor=request.user,
                promotion=promotion,
                data=serializer.validated_data,
            )
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(PromotionSerializer(promotion).data)


class StaffPromotionApproveView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def post(self, request: Request, slug: str) -> Response:
        promotion = get_promotion_by_slug(slug, public_only=False)
        if promotion is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            promotion = approve_promotion(actor=request.user, promotion=promotion)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(PromotionSerializer(promotion).data)


class StaffPromotionRejectView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCatalogueEditor]

    def post(self, request: Request, slug: str) -> Response:
        promotion = get_promotion_by_slug(slug, public_only=False)
        if promotion is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            promotion = reject_promotion(actor=request.user, promotion=promotion)
        except CatalogueServiceError as exc:
            return _service_error(exc)
        return Response(PromotionSerializer(promotion).data)
