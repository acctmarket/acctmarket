# ruff: noqa
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views import defaults as default_views

from acctmarket.applications.users.views import CustomLoginView

urlpatterns = [
    path(
        "", include(
            "acctmarket.applications.home.urls", namespace="homeapp"
        )
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path(
        "users/",
        include(
            "acctmarket.applications.users.urls",
            namespace="users"
        )
    ),
    #  ecomercce manaement
    path(
        "ecommerce/",
        include(
            "acctmarket.applications.ecommerce.urls",
            namespace="ecommerce"
        ),
    ),
    # blog management
    path(
        "blog/",
        include("acctmarket.applications.blog.urls", namespace="blog")
    ),
    # support management
    path(
        "support/",
        include("acctmarket.applications.support.urls", namespace="support"),
    ),
    path(
        "referal/",
        include("acctmarket.applications.refer.urls", namespace="refer")
    ),
    path("accounts/login/", CustomLoginView.as_view(), name="account_login"),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path("ckeditor/", include("ckeditor_uploader.urls")),
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for
    # local web socket development
    urlpatterns += staticfiles_urlpatterns()


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls))
        ] + urlpatterns
