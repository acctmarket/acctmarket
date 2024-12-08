from django.forms import ModelForm, Textarea, TextInput

from acctmarket.applications.support.models import (FrequestAskQuestion,
                                                    Response, Ticket)


class FAQForm(ModelForm):
    class Meta:
        model = FrequestAskQuestion
        fields = ["title", "content"]


class TicketForm(ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description"]
        widgets = {
            "title": TextInput(attrs={"class": "form-control"}),
            "description": Textarea(attrs={"class": "form-control"}),
        }


class ResponseForm(ModelForm):
    class Meta:
        model = Response
        fields = ["messages"]
        widgets = {
            "message": Textarea(attrs={"class": "form-control"}),
        }
