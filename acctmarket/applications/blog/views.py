from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from acctmarket.applications.blog.forms import (Banner, BannerForm,
                                                BlogCategory, BlogCategoryForm,
                                                Post, PostForm)
from acctmarket.utils.mixins import ContentManagerRequiredMixin

# Create your views here.


class SlugMixin:
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        """
        Retrieves an object from the queryset based on the provided slug.

        Parameters:
            queryset (QuerySet, optional): The queryset to filter the objects.
            If not provided, the default queryset is used.

        Returns:
            object: The object with the matching slug.
            If no object is found, a Http404 exception is raised.
        """
        if queryset is None:
            queryset = self.get_queryset()
        slug = self.kwargs.get(self.slug_url_kwarg)
        queryset = queryset.filter(**{self.slug_field: slug})
        return get_object_or_404(queryset)


class CreateBlogCategory(ContentManagerRequiredMixin, CreateView):
    model = BlogCategory
    form_class = BlogCategoryForm
    template_name = "pages/blog/create_blog_category.html"
    success_url = reverse_lazy("blog:category_list")


class CategoryListView(ContentManagerRequiredMixin, ListView):
    model = BlogCategory
    template_name = "pages/blog/category_list.html"
    paginate_by = 10

    def get_queryset(self):
        return BlogCategory.objects.annotate(
            total_products=Count("post")).order_by(
                "-created_at",
        )


class EditPostCategoryView(
    ContentManagerRequiredMixin, SlugMixin, UpdateView
):
    model = BlogCategory
    form_class = BlogCategoryForm
    template_name = "pages/blog/create_blog_category.html"
    success_url = reverse_lazy("blog:category_list")


class DeletePostCategoryView(
    ContentManagerRequiredMixin, SlugMixin, DeleteView
):
    model = BlogCategory
    template_name = "pages/blog/confirm_delete.html"
    success_url = reverse_lazy("blog:category_list")


# =======================================  Blog Categories ends here


class CreateBlogPostView(ContentManagerRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "pages/blog/create_blog_post.html"
    success_url = reverse_lazy("blog:blog_list")


class BlogListView(ContentManagerRequiredMixin, ListView):
    model = Post
    paginate_by = 10
    template_name = "pages/blog/blog_list.html"

    def get_queryset(self):
        return Post.objects.all().order_by("-created_at")


class BlogEditView(ContentManagerRequiredMixin, SlugMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = "pages/blog/create_blog_post.html"
    success_url = reverse_lazy("blog:blog_list")


class BlogDeleteView(ContentManagerRequiredMixin, SlugMixin, DeleteView):
    model = Post
    template_name = "pages/blog/delete_blog.html"
    success_url = reverse_lazy("blog:blog_list")


class BlogViews(ListView):
    model = Post
    template_name = "pages/blog/blog_views.html"
    context_object_name = "blog_posts"
    paginate_by = 5

    def get_queryset(self):
        return Post.objects.all().order_by("-created_at")


class BlogDetailView(DetailView):
    model = Post
    template_name = "pages/blog/blog_details.html"
    context_object_name = "blog_post"
    slug_field = "slug"
    slug_url_kwarg = "slug"


# =======================================  End if blog section


class BannerCreateView(ContentManagerRequiredMixin, CreateView):
    model = Banner
    form_class = BannerForm
    template_name = "pages/blog/create_home_banner.html"
    success_url = reverse_lazy("blog:list_banner")


class BannerEditView(ContentManagerRequiredMixin, SlugMixin, UpdateView):
    model = Banner
    form_class = BannerForm
    template_name = "pages/blog/create_home_banner.html"
    success_url = reverse_lazy("blog:list_banner")


class BannerDeleteView(ContentManagerRequiredMixin, SlugMixin, DeleteView):
    model = Banner
    template_name = "pages/blog/delete_banner.html"
    success_url = reverse_lazy("blog:list_banner")


class BannerListView(ContentManagerRequiredMixin, ListView):
    model = Banner
    paginate_by = 10
    template_name = "pages/blog/banner_list.html"
    context_object_name = "banners"
