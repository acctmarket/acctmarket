from django.urls import path

from acctmarket.applications.support.views import (CreateFAQ, DeleteFAQViews,
                                                   EditFAQViews, FAQListView,
                                                   HELPOrFAQPage,
                                                   TicketDetailView,
                                                   TicketListView)

app_name = "support"
urlpatterns = [
    path("tickets", TicketListView.as_view(), name="ticket_list"),
    path("<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
    path("create-faq", CreateFAQ.as_view(), name="create_faq"),
    path("edit-faq/<int:pk>/", EditFAQViews.as_view(), name="edit_faq"),
    path("delete-faq/<int:pk>/", DeleteFAQViews.as_view(), name="delete_faq"),
    path("faq-list", FAQListView.as_view(), name="faq_list"),
    path("help", HELPOrFAQPage.as_view(), name="helppage"),
]
