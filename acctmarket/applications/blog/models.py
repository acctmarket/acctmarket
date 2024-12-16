import auto_prefetch
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models import (CASCADE, SET_NULL, BooleanField, CharField,
                              SlugField)
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager

from acctmarket.applications.ecommerce.models import CharUUIDTaggedItem
from acctmarket.utils.models import (ImageTitleTimeBaseModels,
                                     TitleTimeBasedModel)

# Create your models here.


class BlogCategory(ImageTitleTimeBaseModels):
    slug = SlugField(default="", blank=True)
    sub_category = auto_prefetch.ForeignKey(
        "self",
        on_delete=CASCADE,
        blank=True,
        null=True,
        related_name="subcategories",
    )

    class Meta:
        verbose_name_plural = "Blog Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Post(ImageTitleTimeBaseModels):
    user = auto_prefetch.ForeignKey(
        "users.User",
        verbose_name=_("User Post"),
        on_delete=SET_NULL,
        null=True,
    )
    slug = SlugField(default="", blank=True)
    category = auto_prefetch.ForeignKey(
        BlogCategory,
        verbose_name=_("Blog Category"),
        on_delete=SET_NULL,
        null=True,
    )

    tags = TaggableManager(
        through=CharUUIDTaggedItem,
        blank=True,
        help_text="A comma-separated list of tags.",
    )
    content = RichTextUploadingField("Description", default="", null=True)

    class Meta:
        verbose_name_plural = "Posts"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return self.slug

    def __str__(self):
        return self.title


class Banner(ImageTitleTimeBaseModels):
    featured_category = auto_prefetch.ForeignKey(
        "ecommerce.Category",
        verbose_name="Banner category",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        help_text="choose products by category only",
    )
    featured_product = auto_prefetch.ForeignKey(
        "ecommerce.Product",
        verbose_name="Banner product",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        help_text="choose products by a particular product only",
    )
    slug = SlugField(default="", blank=True)
    sub_title = CharField(max_length=50, default="", blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_redirect_url(self):
        if self.featured_product:
            return reverse(
                "homeapp:product_detail",
                kwargs={"pk": self.featured_product.pk},
            )
        if self.featured_category:
            return reverse(
                "homeapp:category_list",
                kwargs={"category_slug": self.featured_category.slug},
            )
        return "#"


class Announcement(TitleTimeBasedModel):
    content = RichTextUploadingField("Description", default="", null=True)
    active = BooleanField(default=True)

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return self.title
