from django.urls import path

from acctmarket.applications.users.views import (accountant_account,
                                                 administrator_account,
                                                 content_manager_account,
                                                 content_manager_dashboard,
                                                 customer_dashboard,
                                                 customer_support_reps,
                                                 customers_account,
                                                 dashboard_view, resend_otp,
                                                 superuser, user_detail_view,
                                                 user_redirect_view,
                                                 user_update_view, verify_otp)

app_name = "users"
urlpatterns = [
    path(
        "signup/adminstrator-signup",
        view=administrator_account,
        name="administrator_account",
    ),
    path(
        "signup/content-manager",
        view=content_manager_account,
        name="content_manager_account",
    ),
    path(
        "signup/accountant", view=accountant_account,
        name="accountant_account"),
    path(
        "signup/customer-support",
        view=customer_support_reps,
        name="customer_support_reps",
    ),
    path("signup/customer", view=customers_account, name="customers_account"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
    path("signup/superuser", view=superuser, name="superuser"),

    path("dashboard", view=dashboard_view, name="dashboard_view"),
    path(
        "dashboard/customer",
        view=customer_dashboard,
        name="customer_dashboard"
    ),
    path(
        "dashboard/content-manager",
        view=content_manager_dashboard,
        name="content_manager_dashboard"
    ),

    path(
        "verify-otp/<slug:user_id>/",
        view=verify_otp, name="verify_otp"
    ),
    path("resend-otp/<slug:user_id>/", view=resend_otp, name="resend_otp"),




]
