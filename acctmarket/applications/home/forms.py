from django.forms import EmailInput, ModelForm, Textarea, TextInput

from acctmarket.applications.support.models import ContactUs


class ContactForm(ModelForm):
    class Meta:
        model = ContactUs
        fields = [
            "name", "email",
            "subject", "message"
        ]

        widgets = {
            "name": TextInput(attrs={
                # "class": "form-control",
                "placeholder": "Enter your Name",
            }),

            "email": EmailInput(attrs={
                # "class": "form-control",
                "placeholder": "Enter your Email",
            }),

            "subject": TextInput(attrs={
                # "class": "form-control",
                "placeholder": "Enter your Subject",
            }),

            "message": Textarea(attrs={
                # "class": "form-control",
                "placeholder": "Enter your Message",
                "rows": 5
            }),
        }
