from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django.views.generic import (DetailView, FormView, ListView, TemplateView,
                                  View)

from acctmarket.applications.blog.models import Announcement
from acctmarket.applications.ecommerce.forms import ProductReviewForm
from acctmarket.applications.ecommerce.models import (CartOrder,
                                                      CartOrderItems, Category,
                                                      Product, ProductImages,
                                                      ProductReview)
from acctmarket.applications.home.forms import ContactForm

# Create your views here.


class HomeView(ListView):
    template_name = "pages/home.html"
    model = Announcement

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        announcements = Announcement.objects.filter(active=True).order_by(
            "-created_at",
        )
        context["announcements"] = announcements
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
    login_url = reverse_lazy(
        "login",
    )  # Assuming "login" is the name of the login URL pattern

    def dispatch(self, request, *args, **kwargs):
        if not request.user.administrator_profile.exists():
            # If the user is not an administrator,
            # redirect them to another page
            return redirect(
                reverse_lazy("not_administrator"),
            )
        # Assuming "not_administrator"
        # is the name of the URL pattern for the page
        return super().dispatch(request, *args, **kwargs)


class ProductShopListView(ListView):
    model = Product
    template_name = "pages/shop_lists.html"
    paginate_by = 8
    context_object_name = "all_products"

    def get_queryset(self):
        # Add ordering to the queryset
        products = Product.objects.filter(visible=True).order_by("id")
        for product in products:
            product.discount_info = product.get_applicable_discount()
            print(f" shoplist Discount info for {product.title}: {product.discount_info}")  # noqa
        return products

    def get_context_data(self, **kwargs):
        """Add pagination context data."""
        context = super().get_context_data(**kwargs)
        context["page_obj"] = context["paginator"].page(
            context["page_obj"].number,
        )  # Set page_obj
        return context

    # Add filter functionality
    def post(self, request, *args, **kwargs):
        return ProductFilterView.as_view()(request, *args, **kwargs)


class ProductShopDetailView(DetailView):
    model = Product
    template_name = "pages/shop_details.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        category = product.category

        # fetching the product images
        product_images = ProductImages.objects.filter(product=product)
        # related products in the same category
        related_products = Product.objects.filter(category=category).exclude(
            id=product.id,
        )
        # reviews for the products
        product_reviews = ProductReview.objects.filter(product=product).order_by(   # noqa
            "-created_at",
        )

        review_form = ProductReviewForm()
        make_review = True

        if self.request.user.is_authenticated:
            # Check if the authenticated user has
            # already submitted a review for this product
            users_review_count = ProductReview.objects.filter(
                user=self.request.user,
                product=product,
            ).count()
            if users_review_count > 0:
                make_review = False

        context["product_images"] = product_images
        context["related_product"] = related_products
        context["form"] = review_form
        context["reviews"] = product_reviews
        context["make_review"] = make_review
        return context


class ProductsCategoryList(ListView):
    model = Product
    template_name = "pages/shop_by_category.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        # Get the category based on the slug in the URL
        category_slug = self.kwargs.get("category_slug")
        print("cccccccccc", category_slug)

        # Safely get the category or return 404 if not found
        category = get_object_or_404(Category, slug=category_slug)
        print(category, "xxxx")

        # Filter products based on the category or its subcategories
        products = Product.objects.filter(
            Q(category=category) | Q(category__sub_category=category)
        ).distinct().order_by("-created_at")
        for product in products:
            product.discount_info = product.get_applicable_discount()
            print(f" shoplist Discount info for {product.title}: {product.discount_info}")  # noqa
        return products

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the current category for use in templates
        category_slug = self.kwargs.get("category_slug")
        category = get_object_or_404(Category, slug=category_slug)

        context["category"] = category
        context["subcategories"] = category.subcategories.all()

        return context

    # Add filter functionality
    def post(self, request, *args, **kwargs):
        # Delegate post requests to the
        # ProductFilterView for filtering functionality
        return ProductFilterView.as_view()(request, *args, **kwargs)


class ProductTagsList(ListView):
    model = Product
    template_name = "pages/shop_by_tag.html"
    context_object_name = "products"
    paginate_by = 8

    def get_queryset(self):
        # get the category base on the slug in the url
        tag_slug = self.kwargs["tag_slug"]
        return Product.objects.filter(tags__slug=tag_slug).order_by("created_at")                      # noqa

    # Add filter functionality
    def post(self, request, *args, **kwargs):
        return ProductFilterView.as_view()(request, *args, **kwargs)


class ProductSearchView(ListView):
    model = Product
    template_name = "pages/product_search.html"
    context_object_name = "all_products"
    paginate_by = 8

    def get_queryset(self):
        query = self.request.GET.get("q")
        return Product.objects.filter(
            title__icontains=query,
        )

    def get_context_data(self, **kwargs):
        """Add pagination context data."""
        context = super().get_context_data(**kwargs)
        context["page_obj"] = context["paginator"].page(
            context["page_obj"].number,
        )  # Set page_obj
        return context

    # Add filter functionality
    def post(self, request, *args, **kwargs):
        return ProductFilterView.as_view()(request, *args, **kwargs)


class ProductFilterView(View):
    # Handle GET requests
    def get(self, request, *args, **kwargs):
        # Get the filter criteria from the request
        categories = request.GET.getlist("category[]")
        min_price = request.GET.get("min_price")
        max_price = request.GET.get("max_price")

        try:
            # Filter products that are in stock and digital
            products = Product.objects.filter(in_stock=True, digital=True)

            # Apply the minimum price filter if provided
            if min_price is not None and min_price != "":
                min_price = float(min_price)
                products = products.filter(price__gte=min_price)

            # Apply the maximum price filter if provided
            if max_price is not None and max_price != "":
                max_price = float(max_price)
                products = products.filter(price__lte=max_price)

            # Apply the category filter if provided
            if categories:
                products = products.filter(category__id__in=categories)

            # Prepare the context with the filtered products
            context = {"products": products}

            # Log the context data for debugging

            # Render the HTML for the filtered products using a template
            data = render_to_string("pages/async/product_filter.html", context)

            # Return the rendered HTML as a JSON response
            return JsonResponse({"data": data})

        except (ValidationError, DatabaseError):
            # Log the error for debugging
            # Return an error message as a JSON response
            return JsonResponse(
                {"error": "An error occurred while filtering products."},
                status=500,
            )


class OrderDetails(LoginRequiredMixin, DetailView):
    model = CartOrder
    template_name = "pages/order_details.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = CartOrder.objects.get(user=self.request.user)
        products = CartOrderItems.objects.filter(order=order)

        context["products"] = products
        return context


class ContactPage(FormView):
    template_name = "pages/contact_page.html"
    form_class = ContactForm
    success_url = reverse_lazy("homeapp:contact_success")

    def form_valid(self, form):
        contact = form.save()

        # Render the email content from a template
        subject = f"New Contact Us Message from {contact.name}"
        html_message = render_to_string(
            "pages/contact_email.html", {"contact": contact})
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        print(from_email, "oooooooooooo")
        to_email = settings.EMAIL_HOST_USER
        print(to_email, "kkkkkkkkkkkkkkkkkkkkkkkkkk")
        print(from_email, "xxxxxxxxxxxxxxxxxxxxxxxxxx")

        # Send the email
        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
        return super().form_valid(form)


class ContactSuccessPage(TemplateView):
    template_name = "pages/contact_success.html"


class TermsPolicy(TemplateView):
    template_name = "pages/terms_and_conditions.html"
