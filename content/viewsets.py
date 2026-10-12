"""
HTTP endpoints for `content`.

Public reads + staff management. Business rules live in services.py.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from .models import PublishStatus
from .permissions import IsContentEditor, IsContentStaff
from .selectors import (
    article_by_slug,
    articles_public,
    articles_staff,
    faq_by_id,
    faqs_public,
    faqs_staff,
    resource_by_slug,
    resource_categories,
    resource_category_by_slug,
    resources_public,
    resources_staff,
    rtsa_by_slug,
    rtsa_public,
    rtsa_staff,
    testimonial_by_id,
    testimonials_public,
    testimonials_staff,
)
from .serializers import (
    ArticlePublicSerializer,
    ArticleSerializer,
    ContentStatusSerializer,
    FAQPublicSerializer,
    FAQSerializer,
    ResourceCategorySerializer,
    ResourcePublicSerializer,
    ResourceSerializer,
    RTSAGuidancePublicSerializer,
    RTSAGuidanceSerializer,
    TestimonialPublicSerializer,
    TestimonialSerializer,
)
from .services import (
    ContentServiceError,
    approve_article,
    approve_faq,
    approve_resource,
    approve_rtsa,
    approve_testimonial,
    create_article,
    create_faq,
    create_resource,
    create_resource_category,
    create_rtsa,
    create_testimonial,
    deactivate_article,
    deactivate_faq,
    deactivate_resource,
    deactivate_rtsa,
    deactivate_testimonial,
    reject_article,
    reject_faq,
    reject_resource,
    reject_rtsa,
    reject_testimonial,
    submit_article,
    submit_faq,
    submit_resource,
    submit_rtsa,
    submit_testimonial,
    update_article,
    update_faq,
    update_resource,
    update_resource_category,
    update_rtsa,
    update_testimonial,
)


def _service_error(exc: ContentServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


def _public_or_404(obj, *, public_only: bool):
    if obj is None:
        return None
    if public_only and obj.status != PublishStatus.APPROVED:
        return None
    return obj


# --- Public ---


class PublicFAQListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(FAQPublicSerializer(faqs_public(), many=True).data)


class PublicFAQDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, faq_id: int) -> Response:
        faq = faq_by_id(faq_id=faq_id)
        faq = _public_or_404(faq, public_only=True)
        if faq is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(FAQPublicSerializer(faq).data)


class PublicRTSAListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(RTSAGuidancePublicSerializer(rtsa_public(), many=True).data)


class PublicRTSADetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        item = rtsa_by_slug(slug=slug)
        item = _public_or_404(item, public_only=True)
        if item is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RTSAGuidancePublicSerializer(item).data)


class PublicArticleListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(ArticlePublicSerializer(articles_public(), many=True).data)


class PublicArticleDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        article = article_by_slug(slug=slug)
        article = _public_or_404(article, public_only=True)
        if article is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ArticlePublicSerializer(article).data)


class PublicResourceCategoryListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(ResourceCategorySerializer(resource_categories(), many=True).data)


class PublicResourceListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(ResourcePublicSerializer(resources_public(), many=True).data)


class PublicResourceDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        from .models import ResourceVisibility

        resource = resource_by_slug(slug=slug)
        if (
            resource is None
            or resource.status != PublishStatus.APPROVED
            or resource.visibility != ResourceVisibility.PUBLIC
        ):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResourcePublicSerializer(resource).data)


class PublicTestimonialListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(
            TestimonialPublicSerializer(testimonials_public(), many=True).data
        )


# --- Staff helpers ---


class StaffListCreateMixin:
    """GET list (any staff) / POST create (editors)."""

    list_selector = None
    serializer_class = None
    create_service = None

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsContentStaff()]
        return [IsAuthenticated(), IsContentEditor()]

    def get(self, request: Request) -> Response:
        return Response(self.serializer_class(self.list_selector(), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obj = self.create_service(actor=request.user, data=serializer.validated_data)
        except ContentServiceError as exc:
            return _service_error(exc)
        return Response(
            self.serializer_class(obj).data,
            status=status.HTTP_201_CREATED,
        )


class StaffDetailMixin:
    """GET any staff / PATCH editors."""

    serializer_class = None
    update_service = None
    lookup_kwarg = "slug"

    def get_permissions(self):
        return [IsAuthenticated(), IsContentStaff()]

    def get_object(self, **kwargs):
        raise NotImplementedError

    def get(self, request: Request, **kwargs) -> Response:
        obj = self.get_object(**kwargs)
        if obj is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.serializer_class(obj).data)

    def patch(self, request: Request, **kwargs) -> Response:
        if not IsContentEditor().has_permission(request, self):
            return Response(
                {"detail": "Content editor access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        obj = self.get_object(**kwargs)
        if obj is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            obj = self.update_service(
                actor=request.user,
                **{self._update_kwarg(): obj},
                data=serializer.validated_data,
            )
        except ContentServiceError as exc:
            return _service_error(exc)
        return Response(self.serializer_class(obj).data)

    def _update_kwarg(self) -> str:
        raise NotImplementedError


class StaffActionView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsContentEditor]
    serializer_class = None
    action_service = None
    pass_note = False

    def get_object(self, **kwargs):
        raise NotImplementedError

    def object_kwarg(self) -> str:
        raise NotImplementedError

    def post(self, request: Request, **kwargs) -> Response:
        obj = self.get_object(**kwargs)
        if obj is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        note = ""
        if self.pass_note:
            body = ContentStatusSerializer(data=request.data)
            body.is_valid(raise_exception=True)
            note = body.validated_data.get("note", "")
        try:
            call_kwargs = {"actor": request.user, self.object_kwarg(): obj}
            if self.pass_note:
                call_kwargs["note"] = note
            obj = self.action_service(**call_kwargs)
        except ContentServiceError as exc:
            return _service_error(exc)
        return Response(self.serializer_class(obj).data)


# --- Staff: FAQs ---


class StaffFAQListCreateView(StaffListCreateMixin, RoadstarAPIView):
    list_selector = staticmethod(faqs_staff)
    serializer_class = FAQSerializer
    create_service = staticmethod(create_faq)


class StaffFAQDetailView(StaffDetailMixin, RoadstarAPIView):
    serializer_class = FAQSerializer
    update_service = staticmethod(update_faq)

    def get_object(self, faq_id: int):
        return faq_by_id(faq_id=faq_id)

    def _update_kwarg(self) -> str:
        return "faq"


class StaffFAQSubmitView(StaffActionView):
    serializer_class = FAQSerializer
    action_service = staticmethod(submit_faq)

    def get_object(self, faq_id: int):
        return faq_by_id(faq_id=faq_id)

    def object_kwarg(self) -> str:
        return "faq"


class StaffFAQApproveView(StaffActionView):
    serializer_class = FAQSerializer
    action_service = staticmethod(approve_faq)

    def get_object(self, faq_id: int):
        return faq_by_id(faq_id=faq_id)

    def object_kwarg(self) -> str:
        return "faq"


class StaffFAQRejectView(StaffActionView):
    serializer_class = FAQSerializer
    action_service = staticmethod(reject_faq)
    pass_note = True

    def get_object(self, faq_id: int):
        return faq_by_id(faq_id=faq_id)

    def object_kwarg(self) -> str:
        return "faq"


class StaffFAQDeactivateView(StaffActionView):
    serializer_class = FAQSerializer
    action_service = staticmethod(deactivate_faq)

    def get_object(self, faq_id: int):
        return faq_by_id(faq_id=faq_id)

    def object_kwarg(self) -> str:
        return "faq"


# --- Staff: RTSA ---


class StaffRTSAListCreateView(StaffListCreateMixin, RoadstarAPIView):
    list_selector = staticmethod(rtsa_staff)
    serializer_class = RTSAGuidanceSerializer
    create_service = staticmethod(create_rtsa)


class StaffRTSADetailView(StaffDetailMixin, RoadstarAPIView):
    serializer_class = RTSAGuidanceSerializer
    update_service = staticmethod(update_rtsa)

    def get_object(self, slug: str):
        return rtsa_by_slug(slug=slug)

    def _update_kwarg(self) -> str:
        return "item"


class StaffRTSASubmitView(StaffActionView):
    serializer_class = RTSAGuidanceSerializer
    action_service = staticmethod(submit_rtsa)

    def get_object(self, slug: str):
        return rtsa_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "item"


class StaffRTSAApproveView(StaffActionView):
    serializer_class = RTSAGuidanceSerializer
    action_service = staticmethod(approve_rtsa)

    def get_object(self, slug: str):
        return rtsa_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "item"


class StaffRTSARejectView(StaffActionView):
    serializer_class = RTSAGuidanceSerializer
    action_service = staticmethod(reject_rtsa)
    pass_note = True

    def get_object(self, slug: str):
        return rtsa_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "item"


class StaffRTSADeactivateView(StaffActionView):
    serializer_class = RTSAGuidanceSerializer
    action_service = staticmethod(deactivate_rtsa)

    def get_object(self, slug: str):
        return rtsa_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "item"


# --- Staff: Articles ---


class StaffArticleListCreateView(StaffListCreateMixin, RoadstarAPIView):
    list_selector = staticmethod(articles_staff)
    serializer_class = ArticleSerializer
    create_service = staticmethod(create_article)


class StaffArticleDetailView(StaffDetailMixin, RoadstarAPIView):
    serializer_class = ArticleSerializer
    update_service = staticmethod(update_article)

    def get_object(self, slug: str):
        return article_by_slug(slug=slug)

    def _update_kwarg(self) -> str:
        return "article"


class StaffArticleSubmitView(StaffActionView):
    serializer_class = ArticleSerializer
    action_service = staticmethod(submit_article)

    def get_object(self, slug: str):
        return article_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "article"


class StaffArticleApproveView(StaffActionView):
    serializer_class = ArticleSerializer
    action_service = staticmethod(approve_article)

    def get_object(self, slug: str):
        return article_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "article"


class StaffArticleRejectView(StaffActionView):
    serializer_class = ArticleSerializer
    action_service = staticmethod(reject_article)
    pass_note = True

    def get_object(self, slug: str):
        return article_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "article"


class StaffArticleDeactivateView(StaffActionView):
    serializer_class = ArticleSerializer
    action_service = staticmethod(deactivate_article)

    def get_object(self, slug: str):
        return article_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "article"


# --- Staff: Resource categories ---


class StaffResourceCategoryListCreateView(StaffListCreateMixin, RoadstarAPIView):
    list_selector = staticmethod(resource_categories)
    serializer_class = ResourceCategorySerializer
    create_service = staticmethod(create_resource_category)


class StaffResourceCategoryDetailView(StaffDetailMixin, RoadstarAPIView):
    serializer_class = ResourceCategorySerializer
    update_service = staticmethod(update_resource_category)

    def get_object(self, slug: str):
        return resource_category_by_slug(slug=slug)

    def _update_kwarg(self) -> str:
        return "category"


# --- Staff: Resources ---


class StaffResourceListCreateView(StaffListCreateMixin, RoadstarAPIView):
    list_selector = staticmethod(resources_staff)
    serializer_class = ResourceSerializer
    create_service = staticmethod(create_resource)


class StaffResourceDetailView(StaffDetailMixin, RoadstarAPIView):
    serializer_class = ResourceSerializer
    update_service = staticmethod(update_resource)

    def get_object(self, slug: str):
        return resource_by_slug(slug=slug)

    def _update_kwarg(self) -> str:
        return "resource"


class StaffResourceSubmitView(StaffActionView):
    serializer_class = ResourceSerializer
    action_service = staticmethod(submit_resource)

    def get_object(self, slug: str):
        return resource_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "resource"


class StaffResourceApproveView(StaffActionView):
    serializer_class = ResourceSerializer
    action_service = staticmethod(approve_resource)

    def get_object(self, slug: str):
        return resource_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "resource"


class StaffResourceRejectView(StaffActionView):
    serializer_class = ResourceSerializer
    action_service = staticmethod(reject_resource)
    pass_note = True

    def get_object(self, slug: str):
        return resource_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "resource"


class StaffResourceDeactivateView(StaffActionView):
    serializer_class = ResourceSerializer
    action_service = staticmethod(deactivate_resource)

    def get_object(self, slug: str):
        return resource_by_slug(slug=slug)

    def object_kwarg(self) -> str:
        return "resource"


# --- Staff: Testimonials ---


class StaffTestimonialListCreateView(StaffListCreateMixin, RoadstarAPIView):
    list_selector = staticmethod(testimonials_staff)
    serializer_class = TestimonialSerializer
    create_service = staticmethod(create_testimonial)


class StaffTestimonialDetailView(StaffDetailMixin, RoadstarAPIView):
    serializer_class = TestimonialSerializer
    update_service = staticmethod(update_testimonial)

    def get_object(self, testimonial_id: int):
        return testimonial_by_id(testimonial_id=testimonial_id)

    def _update_kwarg(self) -> str:
        return "testimonial"


class StaffTestimonialSubmitView(StaffActionView):
    serializer_class = TestimonialSerializer
    action_service = staticmethod(submit_testimonial)

    def get_object(self, testimonial_id: int):
        return testimonial_by_id(testimonial_id=testimonial_id)

    def object_kwarg(self) -> str:
        return "testimonial"


class StaffTestimonialApproveView(StaffActionView):
    serializer_class = TestimonialSerializer
    action_service = staticmethod(approve_testimonial)

    def get_object(self, testimonial_id: int):
        return testimonial_by_id(testimonial_id=testimonial_id)

    def object_kwarg(self) -> str:
        return "testimonial"


class StaffTestimonialRejectView(StaffActionView):
    serializer_class = TestimonialSerializer
    action_service = staticmethod(reject_testimonial)
    pass_note = True

    def get_object(self, testimonial_id: int):
        return testimonial_by_id(testimonial_id=testimonial_id)

    def object_kwarg(self) -> str:
        return "testimonial"


class StaffTestimonialDeactivateView(StaffActionView):
    serializer_class = TestimonialSerializer
    action_service = staticmethod(deactivate_testimonial)

    def get_object(self, testimonial_id: int):
        return testimonial_by_id(testimonial_id=testimonial_id)

    def object_kwarg(self) -> str:
        return "testimonial"
