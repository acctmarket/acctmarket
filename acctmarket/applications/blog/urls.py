from django.urls import path

from acctmarket.applications.blog import views

app_name = "blog"
urlpatterns = [
    path(
        "create-post", views.CreateBlogPostView.as_view(),
        name="create_post"
    ),
    path(
        "create-category", views.CreateBlogCategory.as_view(),
        name="create_category"
    ),
    path(
        "edit-category/<slug:slug>/",
        views.EditPostCategoryView.as_view(),
        name="edit_category",
    ),  # noqa
    path(
        "delete-category/<slug:slug>/",
        views.DeletePostCategoryView.as_view(),
        name="delete_category",
    ),
    path(
        "create-list", views.CategoryListView.as_view(),
        name="category_list"
    ),
    path(
        "blog-list", views.BlogListView.as_view(),
        name="blog_list"
    ),
    path(
        "edit-blog/<slug:slug>/", views.BlogEditView.as_view(),
        name="edit_blog"
    ),
    path(
        "delete-blog/<slug:slug>/",
        views.BlogDeleteView.as_view(),
        name="delete_blog",
    ),
    path("", views.BlogViews.as_view(), name="blog_views"),
    path(
        "blog-detail/<slug:slug>/",
        views.BlogDetailView.as_view(),
        name="blog_detail",
    ),
    path(
        "create-banner", views.BannerCreateView.as_view(),
        name="banner_create"
    ),
    path(
        "list-banner", views.BannerListView.as_view(),
        name="list_banner"
    ),
    path(
        "edit-banner/<slug:slug>/",
        views.BannerEditView.as_view(),
        name="edit_banner",
    ),
    path(
        "delete-banner/<slug:slug>/",
        views.BannerDeleteView.as_view(),
        name="delete_banner",
    ),
]
