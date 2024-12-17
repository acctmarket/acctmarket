# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from acctmarket.applications.support.forms import FAQForm, ResponseForm
from acctmarket.applications.support.models import FrequestAskQuestion, Ticket
from acctmarket.utils.mixins import CustomerSupportRepresentativemixin

# Create your views here.


class CreateFAQ(CustomerSupportRepresentativemixin, CreateView):
    model = FrequestAskQuestion
    form_class = FAQForm
    template_name = "pages/support/create_faq.html"
    success_url = reverse_lazy("support:faq_list")


class FAQListView(CustomerSupportRepresentativemixin, ListView):
    model = FrequestAskQuestion
    template_name = "pages/support/faq_list.html"
    context_object_name = "faqs"


class EditFAQViews(CustomerSupportRepresentativemixin, UpdateView):
    model = FrequestAskQuestion
    form_class = FAQForm
    template_name = "pages/support/create_faq.html"


class DeleteFAQViews(CustomerSupportRepresentativemixin, DeleteView):
    model = FrequestAskQuestion
    template_name = "pages/support/faq_delete.html"
    form_class = FAQForm
    success_url = reverse_lazy("support:faq_list")
    context_object_name = "faq"


class HELPOrFAQPage(ListView):
    model = FrequestAskQuestion
    template_name = "pages/support/help_or_faqpage.html"
    context_object_name = "faqs"


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "pages/support/ticket_detail.html"
    context_object_name = "ticket"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ResponseForm()
        return context


class TicketListView(CustomerSupportRepresentativemixin, ListView):
    model = Ticket
    template_name = "pages/support/ticket_list.html"
    context_object_name = "tickets"

    def get_queryset(self):
        return Ticket.objects.filter(customer=self.request.user)
