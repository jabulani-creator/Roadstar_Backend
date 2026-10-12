"""API input/output shapes for `learning`."""

from rest_framework import serializers

from .models import (
    Attempt,
    AttemptAnswer,
    PracticePaper,
    Question,
    StudyDocument,
    Topic,
)


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ("id", "name", "slug", "description", "sort_order")
        read_only_fields = ("id", "slug")


class QuestionStaffSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source="topic.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "topic",
            "topic_name",
            "prompt",
            "choice_a",
            "choice_b",
            "choice_c",
            "choice_d",
            "correct_choice",
            "explanation",
            "difficulty",
            "status",
            "status_label",
            "is_rights_cleared",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "topic_name",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )


class QuestionExamSerializer(serializers.ModelSerializer):
    """Student-facing while sitting — no correct answer / explanation."""

    topic_name = serializers.CharField(source="topic.name", read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "topic_name",
            "prompt",
            "choice_a",
            "choice_b",
            "choice_c",
            "choice_d",
            "difficulty",
        )
        read_only_fields = fields


class QuestionReviewSerializer(serializers.ModelSerializer):
    """Shown after submit — includes correctness helpers via attempt answer."""

    topic_name = serializers.CharField(source="topic.name", read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "topic_name",
            "prompt",
            "choice_a",
            "choice_b",
            "choice_c",
            "choice_d",
            "correct_choice",
            "explanation",
            "difficulty",
        )
        read_only_fields = fields


class PracticePaperListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PracticePaper
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "time_limit_minutes",
            "pass_mark_percent",
            "question_count",
            "status",
            "status_label",
            "available_to_public_preview",
        )
        read_only_fields = fields

    def get_question_count(self, obj: PracticePaper) -> int:
        if hasattr(obj, "paper_questions"):
            return obj.paper_questions.count()
        return obj.questions.count()


class PracticePaperStaffSerializer(serializers.ModelSerializer):
    question_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
    )
    question_count = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PracticePaper
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "instructions",
            "time_limit_minutes",
            "pass_mark_percent",
            "shuffle_questions",
            "status",
            "status_label",
            "available_to_public_preview",
            "question_ids",
            "question_count",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "status",
            "status_label",
            "question_count",
            "approved_at",
            "created_at",
            "updated_at",
        )

    def get_question_count(self, obj: PracticePaper) -> int:
        return obj.paper_questions.count()


class PracticePaperSitSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = PracticePaper
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "instructions",
            "time_limit_minutes",
            "pass_mark_percent",
            "questions",
        )
        read_only_fields = fields

    def get_questions(self, obj: PracticePaper):
        links = obj.paper_questions.all()
        questions = [link.question for link in links]
        if obj.shuffle_questions:
            # Stable-enough shuffle per request using id salt (not crypto).
            questions = sorted(questions, key=lambda q: (q.id * 7) % 97)
        return QuestionExamSerializer(questions, many=True).data


class StudyDocumentSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(
        source="topic.name", read_only=True, allow_null=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = StudyDocument
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "file_url",
            "topic",
            "topic_name",
            "is_rights_cleared",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "topic_name",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )


class AttemptAnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_choice = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class AttemptAnswersSerializer(serializers.Serializer):
    answers = AttemptAnswerInputSerializer(many=True)


class AttemptAnswerReviewSerializer(serializers.ModelSerializer):
    question = QuestionReviewSerializer(read_only=True)

    class Meta:
        model = AttemptAnswer
        fields = ("question", "selected_choice", "is_correct")
        read_only_fields = fields


class AttemptSerializer(serializers.ModelSerializer):
    paper_title = serializers.CharField(source="paper.title", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    answers = AttemptAnswerReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Attempt
        fields = (
            "id",
            "paper",
            "paper_title",
            "status",
            "status_label",
            "started_at",
            "expires_at",
            "submitted_at",
            "score_correct",
            "score_total",
            "score_percent",
            "passed",
            "answers",
        )
        read_only_fields = fields


class AttemptInProgressSerializer(serializers.ModelSerializer):
    """No answers review / no score spoilers while in progress."""

    paper = PracticePaperSitSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Attempt
        fields = (
            "id",
            "paper",
            "status",
            "status_label",
            "started_at",
            "expires_at",
        )
        read_only_fields = fields
