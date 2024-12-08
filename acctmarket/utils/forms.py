import logging

from allauth.account.utils import send_email_confirmation
from django.conf import settings
from django.forms import CheckboxInput, TextInput, inlineformset_factory

from acctmarket.applications.ecommerce.models import Product, ProductKey

logger = logging.getLogger(__name__)


def get_product_key_formset(extra=1):
    return inlineformset_factory(
        Product,
        ProductKey,
        fields=["key", "password", "is_used"],
        extra=extra,
        widgets={
            "key": TextInput(
                attrs={"class": "form-control", "placeholder": "Enter key"}
            ),
            "password": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter password"
                }
            ),
            "is_used": CheckboxInput(attrs={"class": "form-check-input"}),
        },
    )


def send_custom_email_confirmation(request, user):
    """
    Custom function to send the email confirmation.
    """
    try:
        # Generate the confirmation URL manually or modify if necessary
        confirmation_url = f"{settings.SITE_URL}/accounts/confirm-email/{user.pk}/" # noqa

        # Log the confirmation URL for debugging purposes
        logger.debug(f"Generated confirmation URL: {confirmation_url}")

        # Use the standard method to send the email confirmation
        send_email_confirmation(request, user)

        # Optionally, you can customize the email message here

    except Exception as e:
        logger.error(f"Error while sending email confirmation: {e}")
        raise
