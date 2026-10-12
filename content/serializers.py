"""
API input/output shapes for `content`.
"""

from rest_framework import serializers

from .models import Article, FAQ, RTSAGuidance, Resource, ResourceCategory, Testimonial


class FAQSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FAQ
        fields = (
            "id",
            "question",
            "answer",
            "category",
            "category_label",
            "display_order",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "category_label",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )


class FAQPublicSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = FAQ
        fields = (
            "id",
            "question",
            "answer",
            "category",
            "category_label",
            "display_order",
        )
        read_only_fields = fields


class RTSAGuidanceSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RTSAGuidance
        fields = (
            "id",
            "title",
            "slug",
            "body",
            "fee_amount",
            "currency",
            "source_url",
            "effective_date",
            "last_reviewed_at",
            "display_order",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )


class RTSAGuidancePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = RTSAGuidance
        fields = (
            "id",
            "title",
            "slug",
            "body",
            "fee_amount",
            "currency",
            "source_url",
            "effective_date",
            "last_reviewed_at",
            "display_order",
        )
        read_only_fields = fields


class ArticleSerializer(serializers.ModelSerializer):
    article_type_label = serializers.CharField(
        source="get_article_type_display",
        read_only=True,
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "body",
            "article_type",
            "article_type_label",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "article_type_label",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )


class ArticlePublicSerializer(serializers.ModelSerializer):
    article_type_label = serializers.CharField(
        source="get_article_type_display",
        read_only=True,
    )

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "body",
            "article_type",
            "article_type_label",
            "updated_at",
        )
        read_only_fields = fields


class ResourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceCategory
        fields = ("id", "name", "slug")
        read_only_fields = ("id", "slug")


class ResourceSerializer(serializers.ModelSerializer):
    category_detail = ResourceCategorySerializer(source="category", read_only=True)
    visibility_label = serializers.CharField(
        source="get_visibility_display",
        read_only=True,
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Resource
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "category",
            "category_detail",
            "file_url",
            "visibility",
            "visibility_label",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "category_detail",
            "visibility_label",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )


class ResourcePublicSerializer(serializers.ModelSerializer):
    category_detail = ResourceCategorySerializer(source="category", read_only=True)

    class Meta:
        model = Resource
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "category_detail",
            "file_url",
        )
        read_only_fields = fields


class TestimonialSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    related_course_name = serializers.CharField(
        source="related_course.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Testimonial
        fields = (
            "id",
            "quote",
            "author_name",
            "author_role",
            "related_course",
            "related_course_name",
            "rating",
            "consent_to_publish",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "related_course_name",
            "status",
            "status_label",
            "approved_at",
            "created_at",
            "updated_at",
        )


class TestimonialPublicSerializer(serializers.ModelSerializer):
    related_course_name = serializers.CharField(
        source="related_course.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Testimonial
        fields = (
            "id",
            "quote",
            "author_name",
            "author_role",
            "related_course_name",
            "rating",
        )
        read_only_fields = fields


class ContentStatusSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
