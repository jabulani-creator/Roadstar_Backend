"""
URL routes for `learning`.

Public:
- GET /api/v1/learning/topics/
- GET /api/v1/learning/papers/  (preview metadata only)
- GET /api/v1/learning/study-documents/

Student:
- GET  /api/v1/learning/me/papers/
- GET  /api/v1/learning/me/papers/{slug}/
- GET  /api/v1/learning/me/attempts/
- POST /api/v1/learning/me/papers/{slug}/start/
- GET  /api/v1/learning/me/attempts/{id}/
- POST /api/v1/learning/me/attempts/{id}/save/
- POST /api/v1/learning/me/attempts/{id}/submit/

Staff:
- /api/v1/staff/learning/topics/
- /api/v1/staff/learning/questions/
- /api/v1/staff/learning/papers/
- /api/v1/staff/learning/study-documents/
"""

from django.urls import path

from .viewsets import (
    PublicPaperListView,
    PublicStudyDocumentListView,
    PublicTopicListView,
    StaffPaperApproveView,
    StaffPaperDeactivateView,
    StaffPaperDetailView,
    StaffPaperListCreateView,
    StaffQuestionApproveView,
    StaffQuestionDetailView,
    StaffQuestionListCreateView,
    StaffStudyDocumentApproveView,
    StaffStudyDocumentListCreateView,
    StaffTopicDetailView,
    StaffTopicListCreateView,
    StudentAttemptDetailView,
    StudentAttemptListView,
    StudentAttemptSaveView,
    StudentAttemptStartView,
    StudentAttemptSubmitView,
    StudentPaperDetailView,
    StudentPaperListView,
)

urlpatterns = [
    path("learning/topics/", PublicTopicListView.as_view(), name="public-learning-topics"),
    path("learning/papers/", PublicPaperListView.as_view(), name="public-learning-papers"),
    path(
        "learning/study-documents/",
        PublicStudyDocumentListView.as_view(),
        name="public-learning-study-documents",
    ),
    path(
        "learning/me/papers/",
        StudentPaperListView.as_view(),
        name="student-learning-papers",
    ),
    path(
        "learning/me/papers/<slug:slug>/",
        StudentPaperDetailView.as_view(),
        name="student-learning-paper-detail",
    ),
    path(
        "learning/me/papers/<slug:slug>/start/",
        StudentAttemptStartView.as_view(),
        name="student-learning-attempt-start",
    ),
    path(
        "learning/me/attempts/",
        StudentAttemptListView.as_view(),
        name="student-learning-attempts",
    ),
    path(
        "learning/me/attempts/<int:attempt_id>/",
        StudentAttemptDetailView.as_view(),
        name="student-learning-attempt-detail",
    ),
    path(
        "learning/me/attempts/<int:attempt_id>/save/",
        StudentAttemptSaveView.as_view(),
        name="student-learning-attempt-save",
    ),
    path(
        "learning/me/attempts/<int:attempt_id>/submit/",
        StudentAttemptSubmitView.as_view(),
        name="student-learning-attempt-submit",
    ),
    path(
        "staff/learning/topics/",
        StaffTopicListCreateView.as_view(),
        name="staff-learning-topics",
    ),
    path(
        "staff/learning/topics/<slug:slug>/",
        StaffTopicDetailView.as_view(),
        name="staff-learning-topic-detail",
    ),
    path(
        "staff/learning/questions/",
        StaffQuestionListCreateView.as_view(),
        name="staff-learning-questions",
    ),
    path(
        "staff/learning/questions/<int:question_id>/",
        StaffQuestionDetailView.as_view(),
        name="staff-learning-question-detail",
    ),
    path(
        "staff/learning/questions/<int:question_id>/approve/",
        StaffQuestionApproveView.as_view(),
        name="staff-learning-question-approve",
    ),
    path(
        "staff/learning/papers/",
        StaffPaperListCreateView.as_view(),
        name="staff-learning-papers",
    ),
    path(
        "staff/learning/papers/<slug:slug>/",
        StaffPaperDetailView.as_view(),
        name="staff-learning-paper-detail",
    ),
    path(
        "staff/learning/papers/<slug:slug>/approve/",
        StaffPaperApproveView.as_view(),
        name="staff-learning-paper-approve",
    ),
    path(
        "staff/learning/papers/<slug:slug>/deactivate/",
        StaffPaperDeactivateView.as_view(),
        name="staff-learning-paper-deactivate",
    ),
    path(
        "staff/learning/study-documents/",
        StaffStudyDocumentListCreateView.as_view(),
        name="staff-learning-study-documents",
    ),
    path(
        "staff/learning/study-documents/<slug:slug>/approve/",
        StaffStudyDocumentApproveView.as_view(),
        name="staff-learning-study-document-approve",
    ),
]
