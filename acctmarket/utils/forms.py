from django.forms import CheckboxInput, TextInput, inlineformset_factory

from acctmarket.applications.ecommerce.models import Product, ProductKey


def get_product_key_formset(extra=1):
    return inlineformset_factory(
        Product,
        ProductKey,
        fields=["key", "password", "is_used"],
        extra=extra,
        widgets={
            "key": TextInput(
                attrs={"class": "form-control", "placeholder": "Enter key"},
            ),
            "password": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter password",
                },
            ),
            "is_used": CheckboxInput(attrs={"class": "form-check-input"}),
        },
    )
