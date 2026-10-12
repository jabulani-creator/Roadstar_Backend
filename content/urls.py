"""
URL routes for `content`.

Public:
- GET /api/v1/faqs/
- GET /api/v1/faqs/{id}/
- GET /api/v1/rtsa/
- GET /api/v1/rtsa/{slug}/
- GET /api/v1/articles/
- GET /api/v1/articles/{slug}/
- GET /api/v1/resource-categories/
- GET /api/v1/resources/
- GET /api/v1/resources/{slug}/
- GET /api/v1/testimonials/

Staff:
- /api/v1/staff/faqs/
- /api/v1/staff/rtsa/
- /api/v1/staff/articles/
- /api/v1/staff/resource-categories/
- /api/v1/staff/resources/
- /api/v1/staff/testimonials/
"""

from django.urls import path

from .viewsets import (
    PublicArticleDetailView,
    PublicArticleListView,
    PublicFAQDetailView,
    PublicFAQListView,
    PublicResourceCategoryListView,
    PublicResourceDetailView,
    PublicResourceListView,
    PublicRTSADetailView,
    PublicRTSAListView,
    PublicTestimonialListView,
    StaffArticleApproveView,
    StaffArticleDeactivateView,
    StaffArticleDetailView,
    StaffArticleListCreateView,
    StaffArticleRejectView,
    StaffArticleSubmitView,
    StaffFAQApproveView,
    StaffFAQDeactivateView,
    StaffFAQDetailView,
    StaffFAQListCreateView,
    StaffFAQRejectView,
    StaffFAQSubmitView,
    StaffResourceApproveView,
    StaffResourceCategoryDetailView,
    StaffResourceCategoryListCreateView,
    StaffResourceDeactivateView,
    StaffResourceDetailView,
    StaffResourceListCreateView,
    StaffResourceRejectView,
    StaffResourceSubmitView,
    StaffRTSAApproveView,
    StaffRTSADeactivateView,
    StaffRTSADetailView,
    StaffRTSAListCreateView,
    StaffRTSARejectView,
    StaffRTSASubmitView,
    StaffTestimonialApproveView,
    StaffTestimonialDeactivateView,
    StaffTestimonialDetailView,
    StaffTestimonialListCreateView,
    StaffTestimonialRejectView,
    StaffTestimonialSubmitView,
)

urlpatterns = [
    # Public
    path("faqs/", PublicFAQListView.as_view(), name="public-faq-list"),
    path("faqs/<int:faq_id>/", PublicFAQDetailView.as_view(), name="public-faq-detail"),
    path("rtsa/", PublicRTSAListView.as_view(), name="public-rtsa-list"),
    path("rtsa/<slug:slug>/", PublicRTSADetailView.as_view(), name="public-rtsa-detail"),
    path("articles/", PublicArticleListView.as_view(), name="public-article-list"),
    path(
        "articles/<slug:slug>/",
        PublicArticleDetailView.as_view(),
        name="public-article-detail",
    ),
    path(
        "resource-categories/",
        PublicResourceCategoryListView.as_view(),
        name="public-resource-category-list",
    ),
    path("resources/", PublicResourceListView.as_view(), name="public-resource-list"),
    path(
        "resources/<slug:slug>/",
        PublicResourceDetailView.as_view(),
        name="public-resource-detail",
    ),
    path(
        "testimonials/",
        PublicTestimonialListView.as_view(),
        name="public-testimonial-list",
    ),
    # Staff FAQs
    path("staff/faqs/", StaffFAQListCreateView.as_view(), name="staff-faq-list"),
    path(
        "staff/faqs/<int:faq_id>/",
        StaffFAQDetailView.as_view(),
        name="staff-faq-detail",
    ),
    path(
        "staff/faqs/<int:faq_id>/submit/",
        StaffFAQSubmitView.as_view(),
        name="staff-faq-submit",
    ),
    path(
        "staff/faqs/<int:faq_id>/approve/",
        StaffFAQApproveView.as_view(),
        name="staff-faq-approve",
    ),
    path(
        "staff/faqs/<int:faq_id>/reject/",
        StaffFAQRejectView.as_view(),
        name="staff-faq-reject",
    ),
    path(
        "staff/faqs/<int:faq_id>/deactivate/",
        StaffFAQDeactivateView.as_view(),
        name="staff-faq-deactivate",
    ),
    # Staff RTSA
    path("staff/rtsa/", StaffRTSAListCreateView.as_view(), name="staff-rtsa-list"),
    path(
        "staff/rtsa/<slug:slug>/",
        StaffRTSADetailView.as_view(),
        name="staff-rtsa-detail",
    ),
    path(
        "staff/rtsa/<slug:slug>/submit/",
        StaffRTSASubmitView.as_view(),
        name="staff-rtsa-submit",
    ),
    path(
        "staff/rtsa/<slug:slug>/approve/",
        StaffRTSAApproveView.as_view(),
        name="staff-rtsa-approve",
    ),
    path(
        "staff/rtsa/<slug:slug>/reject/",
        StaffRTSARejectView.as_view(),
        name="staff-rtsa-reject",
    ),
    path(
        "staff/rtsa/<slug:slug>/deactivate/",
        StaffRTSADeactivateView.as_view(),
        name="staff-rtsa-deactivate",
    ),
    # Staff articles
    path(
        "staff/articles/",
        StaffArticleListCreateView.as_view(),
        name="staff-article-list",
    ),
    path(
        "staff/articles/<slug:slug>/",
        StaffArticleDetailView.as_view(),
        name="staff-article-detail",
    ),
    path(
        "staff/articles/<slug:slug>/submit/",
        StaffArticleSubmitView.as_view(),
        name="staff-article-submit",
    ),
    path(
        "staff/articles/<slug:slug>/approve/",
        StaffArticleApproveView.as_view(),
        name="staff-article-approve",
    ),
    path(
        "staff/articles/<slug:slug>/reject/",
        StaffArticleRejectView.as_view(),
        name="staff-article-reject",
    ),
    path(
        "staff/articles/<slug:slug>/deactivate/",
        StaffArticleDeactivateView.as_view(),
        name="staff-article-deactivate",
    ),
    # Staff resource categories
    path(
        "staff/resource-categories/",
        StaffResourceCategoryListCreateView.as_view(),
        name="staff-resource-category-list",
    ),
    path(
        "staff/resource-categories/<slug:slug>/",
        StaffResourceCategoryDetailView.as_view(),
        name="staff-resource-category-detail",
    ),
    # Staff resources
    path(
        "staff/resources/",
        StaffResourceListCreateView.as_view(),
        name="staff-resource-list",
    ),
    path(
        "staff/resources/<slug:slug>/",
        StaffResourceDetailView.as_view(),
        name="staff-resource-detail",
    ),
    path(
        "staff/resources/<slug:slug>/submit/",
        StaffResourceSubmitView.as_view(),
        name="staff-resource-submit",
    ),
    path(
        "staff/resources/<slug:slug>/approve/",
        StaffResourceApproveView.as_view(),
        name="staff-resource-approve",
    ),
    path(
        "staff/resources/<slug:slug>/reject/",
        StaffResourceRejectView.as_view(),
        name="staff-resource-reject",
    ),
    path(
        "staff/resources/<slug:slug>/deactivate/",
        StaffResourceDeactivateView.as_view(),
        name="staff-resource-deactivate",
    ),
    # Staff testimonials
    path(
        "staff/testimonials/",
        StaffTestimonialListCreateView.as_view(),
        name="staff-testimonial-list",
    ),
    path(
        "staff/testimonials/<int:testimonial_id>/",
        StaffTestimonialDetailView.as_view(),
        name="staff-testimonial-detail",
    ),
    path(
        "staff/testimonials/<int:testimonial_id>/submit/",
        StaffTestimonialSubmitView.as_view(),
        name="staff-testimonial-submit",
    ),
    path(
        "staff/testimonials/<int:testimonial_id>/approve/",
        StaffTestimonialApproveView.as_view(),
        name="staff-testimonial-approve",
    ),
    path(
        "staff/testimonials/<int:testimonial_id>/reject/",
        StaffTestimonialRejectView.as_view(),
        name="staff-testimonial-reject",
    ),
    path(
        "staff/testimonials/<int:testimonial_id>/deactivate/",
        StaffTestimonialDeactivateView.as_view(),
        name="staff-testimonial-deactivate",
    ),
]
