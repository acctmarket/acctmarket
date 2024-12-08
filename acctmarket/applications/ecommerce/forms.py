from ckeditor.widgets import CKEditorWidget
from django.forms import (CharField, ChoiceField, FileInput, ModelForm, Select,
                          Textarea, TextInput, inlineformset_factory)
from multiupload.fields import MultiFileField
from taggit.forms import TagField

from acctmarket.applications.ecommerce.models import (Category, Product,
                                                      ProductImages,
                                                      ProductKey,
                                                      ProductReview)
from acctmarket.utils.choices import Rating


class ProductForm(ModelForm):
    description = CharField(
        label="Description",
        widget=CKEditorWidget(
            attrs={
                "class": "form-control",
                "placeholder": "Enter product description"
            },
        ),
    )

    tags = TagField(required=False)

    class Meta:
        model = Product
        fields = [
            "title",
            "image",
            "description",
            "price",
            "oldprice",
            "tags",
            "product_status",
            "category",
            "in_stock",
            "featured",
            "digital",
            "best_seller",
            "special_offer",
            "just_arrived",
            "resource",
            "quantity_in_stock",
            "specification",
        ]


class ProductKeyForm(ModelForm):
    class Meta:
        model = ProductKey
        fields = ["key", "password", "is_used"]


ProductKeyFormSet = inlineformset_factory(
    Product, ProductKey, form=ProductKeyForm, extra=1
)


class ProductImagesForm(ModelForm):
    """Form to get all product images"""

    image = MultiFileField(
        min_num=1, max_num=10,
        max_file_size=1024 * 1024 * 5
    )

    class Meta:
        model = ProductImages
        fields = ["image", "product"]

        widgets = {
            "product": Select(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter product",
                },
            ),
        }


class CategoryForm(ModelForm):
    class Meta:
        model = Category
        fields = ["title", "image", "sub_category"]
        widgets = {
            "title": TextInput(
                attrs={
                    "class": "flex-grow",
                    "placeholder": "Enter category name"
                },
            ),
            "image": FileInput(attrs={
                "class": "form-control", "name": "filename"
            }),
            "sub_category": Select(attrs={"class": "form-control"}),
        }



class ProductReviewForm(ModelForm):    # noqa
    review = CharField(
        widget=Textarea(attrs={"placeholder": "Write your  review"}),
    )
    rating = ChoiceField(
        choices=Rating.choices,
        widget=Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = ProductReview
        fields = ["review", "rating"]


# class NowPaymentForm(ModelForm):
#     pay_currency = ChoiceField(choices=[])
#     order =
