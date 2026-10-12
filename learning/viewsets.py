"""
HTTP endpoints for `learning`.

Public paper preview + student attempts + staff authoring.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from config.api import RoadstarAPIView
from students.selectors import student_for_user

from .models import PublishStatus
from .permissions import IsLearningEditor, IsLearningStaff
from .selectors import (
    attempt_by_id,
    attempts_for_student,
    paper_by_slug,
    papers_for_students,
    papers_public_preview,
    papers_staff,
    question_by_id,
    questions_staff,
    study_document_by_slug,
    study_documents_public,
    study_documents_staff,
    topic_by_slug,
    topics_all,
)
from .serializers import (
    AttemptAnswersSerializer,
    AttemptInProgressSerializer,
    AttemptSerializer,
    PracticePaperListSerializer,
    PracticePaperStaffSerializer,
    QuestionStaffSerializer,
    StudyDocumentSerializer,
    TopicSerializer,
)
from .services import (
    LearningServiceError,
    approve_practice_paper,
    approve_question,
    approve_study_document,
    create_practice_paper,
    create_question,
    create_study_document,
    create_topic,
    deactivate_practice_paper,
    save_attempt_answers,
    start_attempt,
    submit_attempt,
    update_practice_paper,
    update_question,
    update_topic,
)


def _service_error(exc: LearningServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


def _answers_map(validated) -> dict[int, str]:
    return {
        item["question_id"]: item.get("selected_choice") or ""
        for item in validated.get("answers", [])
    }


# --- Public ---


class PublicTopicListView(RoadstarAPIView):
    permission_classes = [AllowAny]
    serializer_class = TopicSerializer

    def get(self, request: Request) -> Response:
        return Response(TopicSerializer(topics_all(), many=True).data)


class PublicPaperListView(RoadstarAPIView):
    permission_classes = [AllowAny]
    serializer_class = PracticePaperListSerializer

    def get(self, request: Request) -> Response:
        return Response(
            PracticePaperListSerializer(papers_public_preview(), many=True).data
        )


class PublicStudyDocumentListView(RoadstarAPIView):
    permission_classes = [AllowAny]
    serializer_class = StudyDocumentSerializer

    def get(self, request: Request) -> Response:
        return Response(
            StudyDocumentSerializer(study_documents_public(), many=True).data
        )


# --- Student portal ---


class StudentPaperListView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PracticePaperListSerializer

    def get(self, request: Request) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            PracticePaperListSerializer(papers_for_students(), many=True).data
        )


class StudentPaperDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PracticePaperListSerializer

    def get(self, request: Request, slug: str) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        paper = paper_by_slug(slug=slug)
        if paper is None or paper.status != PublishStatus.APPROVED:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PracticePaperListSerializer(paper).data)


class StudentAttemptListView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttemptSerializer

    def get(self, request: Request) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = attempts_for_student(student=student)
        # Hide answer spoilers for in-progress in list
        data = []
        for attempt in qs:
            if attempt.status == "in_progress":
                data.append(AttemptInProgressSerializer(attempt).data)
            else:
                data.append(AttemptSerializer(attempt).data)
        return Response(data)


class StudentAttemptStartView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttemptInProgressSerializer

    def post(self, request: Request, slug: str) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        paper = paper_by_slug(slug=slug)
        if paper is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            attempt = start_attempt(student=student, paper=paper)
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(
            AttemptInProgressSerializer(attempt).data,
            status=status.HTTP_201_CREATED,
        )


class StudentAttemptDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttemptSerializer

    def get(self, request: Request, attempt_id: int) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        attempt = attempt_by_id(attempt_id=attempt_id)
        if attempt is None or attempt.student_id != student.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if attempt.status == "in_progress":
            from .services import refresh_attempt

            attempt = refresh_attempt(attempt)
            attempt = attempt_by_id(attempt_id=attempt.id)
        if attempt.status == "in_progress":
            return Response(AttemptInProgressSerializer(attempt).data)
        return Response(AttemptSerializer(attempt).data)


class StudentAttemptSaveView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttemptAnswersSerializer

    def post(self, request: Request, attempt_id: int) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        attempt = attempt_by_id(attempt_id=attempt_id)
        if attempt is None or attempt.student_id != student.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = AttemptAnswersSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            attempt = save_attempt_answers(
                student=student,
                attempt=attempt,
                answers=_answers_map(body.validated_data),
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(AttemptInProgressSerializer(attempt).data)


class StudentAttemptSubmitView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AttemptAnswersSerializer

    def post(self, request: Request, attempt_id: int) -> Response:
        student = student_for_user(user=request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        attempt = attempt_by_id(attempt_id=attempt_id)
        if attempt is None or attempt.student_id != student.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = AttemptAnswersSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            attempt = submit_attempt(
                student=student,
                attempt=attempt,
                answers=_answers_map(body.validated_data),
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        attempt = attempt_by_id(attempt_id=attempt.id)
        return Response(AttemptSerializer(attempt).data)


# --- Staff ---


class StaffTopicListCreateView(RoadstarAPIView):
    serializer_class = TopicSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsLearningStaff()]
        return [IsAuthenticated(), IsLearningEditor()]

    def get(self, request: Request) -> Response:
        return Response(TopicSerializer(topics_all(), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = TopicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            topic = create_topic(actor=request.user, data=serializer.validated_data)
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(TopicSerializer(topic).data, status=status.HTTP_201_CREATED)


class StaffTopicDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningStaff]
    serializer_class = TopicSerializer

    def get(self, request: Request, slug: str) -> Response:
        topic = topic_by_slug(slug=slug)
        if topic is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TopicSerializer(topic).data)

    def patch(self, request: Request, slug: str) -> Response:
        if not IsLearningEditor().has_permission(request, self):
            return Response(
                {"detail": "Learning editor access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        topic = topic_by_slug(slug=slug)
        if topic is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TopicSerializer(topic, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            topic = update_topic(
                actor=request.user, topic=topic, data=serializer.validated_data
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(TopicSerializer(topic).data)


class StaffQuestionListCreateView(RoadstarAPIView):
    serializer_class = QuestionStaffSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsLearningStaff()]
        return [IsAuthenticated(), IsLearningEditor()]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        return Response(
            QuestionStaffSerializer(
                questions_staff(status=status_filter), many=True
            ).data
        )

    def post(self, request: Request) -> Response:
        serializer = QuestionStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            question = create_question(
                actor=request.user, data=serializer.validated_data
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(
            QuestionStaffSerializer(question).data, status=status.HTTP_201_CREATED
        )


class StaffQuestionDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningStaff]
    serializer_class = QuestionStaffSerializer

    def get(self, request: Request, question_id: int) -> Response:
        question = question_by_id(question_id=question_id)
        if question is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuestionStaffSerializer(question).data)

    def patch(self, request: Request, question_id: int) -> Response:
        if not IsLearningEditor().has_permission(request, self):
            return Response(
                {"detail": "Learning editor access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        question = question_by_id(question_id=question_id)
        if question is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuestionStaffSerializer(
            question, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            question = update_question(
                actor=request.user,
                question=question,
                data=serializer.validated_data,
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(QuestionStaffSerializer(question).data)


class StaffQuestionApproveView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningEditor]
    serializer_class = QuestionStaffSerializer

    def post(self, request: Request, question_id: int) -> Response:
        question = question_by_id(question_id=question_id)
        if question is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            question = approve_question(actor=request.user, question=question)
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(QuestionStaffSerializer(question).data)


class StaffPaperListCreateView(RoadstarAPIView):
    serializer_class = PracticePaperStaffSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsLearningStaff()]
        return [IsAuthenticated(), IsLearningEditor()]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        return Response(
            PracticePaperStaffSerializer(
                papers_staff(status=status_filter), many=True
            ).data
        )

    def post(self, request: Request) -> Response:
        serializer = PracticePaperStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            paper = create_practice_paper(
                actor=request.user, data=serializer.validated_data
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(
            PracticePaperStaffSerializer(paper).data, status=status.HTTP_201_CREATED
        )


class StaffPaperDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningStaff]
    serializer_class = PracticePaperStaffSerializer

    def get(self, request: Request, slug: str) -> Response:
        paper = paper_by_slug(slug=slug)
        if paper is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PracticePaperStaffSerializer(paper).data)

    def patch(self, request: Request, slug: str) -> Response:
        if not IsLearningEditor().has_permission(request, self):
            return Response(
                {"detail": "Learning editor access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        paper = paper_by_slug(slug=slug)
        if paper is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PracticePaperStaffSerializer(
            paper, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            paper = update_practice_paper(
                actor=request.user,
                paper=paper,
                data=serializer.validated_data,
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(PracticePaperStaffSerializer(paper).data)


class StaffPaperApproveView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningEditor]
    serializer_class = PracticePaperStaffSerializer

    def post(self, request: Request, slug: str) -> Response:
        paper = paper_by_slug(slug=slug)
        if paper is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            paper = approve_practice_paper(actor=request.user, paper=paper)
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(PracticePaperStaffSerializer(paper).data)


class StaffPaperDeactivateView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningEditor]
    serializer_class = PracticePaperStaffSerializer

    def post(self, request: Request, slug: str) -> Response:
        paper = paper_by_slug(slug=slug)
        if paper is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            paper = deactivate_practice_paper(actor=request.user, paper=paper)
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(PracticePaperStaffSerializer(paper).data)


class StaffStudyDocumentListCreateView(RoadstarAPIView):
    serializer_class = StudyDocumentSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsLearningStaff()]
        return [IsAuthenticated(), IsLearningEditor()]

    def get(self, request: Request) -> Response:
        return Response(
            StudyDocumentSerializer(study_documents_staff(), many=True).data
        )

    def post(self, request: Request) -> Response:
        serializer = StudyDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            doc = create_study_document(
                actor=request.user, data=serializer.validated_data
            )
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(
            StudyDocumentSerializer(doc).data, status=status.HTTP_201_CREATED
        )


class StaffStudyDocumentApproveView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsLearningEditor]
    serializer_class = StudyDocumentSerializer

    def post(self, request: Request, slug: str) -> Response:
        doc = study_document_by_slug(slug=slug)
        if doc is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            doc = approve_study_document(actor=request.user, doc=doc)
        except LearningServiceError as exc:
            return _service_error(exc)
        return Response(StudyDocumentSerializer(doc).data)
