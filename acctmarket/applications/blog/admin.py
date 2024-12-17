from django.contrib import admin

from acctmarket.applications.blog.models import (Announcement, Banner,
                                                 BlogCategory, Post)

# Register your models here.


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ("title",)
    search_fields = ("title",)
    date_hierarchy = "created_at"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "slug", "user", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ("category", "user", "created_at")
    search_fields = ("title", "content")
    date_hierarchy = "created_at"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = [
        "title", "slug", "sub_title",
        "featured_category", "featured_product",
    ]


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "active")
    list_filter = ("active", "created_at")
    search_fields = ("title", "content")
