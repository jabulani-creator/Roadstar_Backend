"""
Django admin for content records.
"""

from django.contrib import admin

from .models import Article, FAQ, RTSAGuidance, Resource, ResourceCategory, Testimonial


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "display_order", "status")
    list_filter = ("category", "status")
    search_fields = ("question", "answer")


@admin.register(RTSAGuidance)
class RTSAGuidanceAdmin(admin.ModelAdmin):
    list_display = ("title", "fee_amount", "effective_date", "last_reviewed_at", "status")
    list_filter = ("status",)
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "article_type", "status", "updated_at")
    list_filter = ("article_type", "status")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "visibility", "status")
    list_filter = ("visibility", "status", "category")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "author_name",
        "consent_to_publish",
        "status",
        "related_course",
        "rating",
    )
    list_filter = ("status", "consent_to_publish")
    search_fields = ("author_name", "quote")
