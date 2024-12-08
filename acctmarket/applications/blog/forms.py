from ckeditor.widgets import CKEditorWidget
from django.forms import FileInput, ModelForm, Select, TextInput

from acctmarket.applications.blog.models import Banner, BlogCategory, Post


class BlogCategoryForm(ModelForm):
    class Meta:
        model = BlogCategory
        fields = [
            "title",
            "image",
            "sub_category",
        ]

        widgets = {
            "title": TextInput(
                attrs={"class": "form-control", "placeholder": "Enter  title"},
            ),
            "image": FileInput(
                attrs={"class": "form-control", "name": "filename"}
            ),
            "sub_category": Select(attrs={"class": "form-control"}),
        }


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = [
            "title",
            "image",
            "content",
            "category",
            "tags",
        ]

        widgets = {
            "title": TextInput(
                attrs={
                    "class": "form-control", "placeholder": "Enter post title"
                },
            ),
            "image": FileInput(attrs={
                "class": "form-control", "name": "filename"
            }),
            "content": CKEditorWidget(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter post content"
                },
            ),
            "category": Select(attrs={"class": "form-control"}),
            "tags": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter tags separate each by comma",
                },
            ),
        }


class BannerForm(ModelForm):
    class Meta:
        model = Banner
        fields = [
            "title",
            "sub_title",
            "image",
            "featured_category",
            "featured_product",
        ]

        widgets = {
            "title": TextInput(
                attrs={
                    "class": "form-control", "placeholder": "Enter short title"
                },
            ),
            "sub_title": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter very short description",
                },
            ),
            "featured_category": Select(attrs={"class": "form-control"}),
            "featured_product": Select(attrs={"class": "form-control"}),
            "image": FileInput(attrs={
                "class": "form-control", "name": "filename"
            }),
        }
