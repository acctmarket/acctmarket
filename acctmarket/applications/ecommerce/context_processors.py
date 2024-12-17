from django.db.models import Max, Min
from django.urls import reverse
from django.utils import timezone

from acctmarket.applications.blog.models import Banner, BlogCategory, Post
from acctmarket.applications.ecommerce.models import (Category, Product,
                                                      WishList)


def product_list(request):
    """
    Context processor to provide a list of products to templates.

    :param request: HTTP request object
    :return: Dictionary containing the product list
    """
    # Fetch all products and prefetch related fields for efficiency
    products = Product.objects.prefetch_related("category").order_by(
        "-created_at", "-updated_at", "-id"
    )

    # Attach discount info to all products
    for product in products:
        product.discount_info = product.get_applicable_discount()
        print(f"Discount info for {product.title}: {product.discount_info}")

    # Use in-memory filtered querysets for subsets to retain discount_info
    visible_products = [
        product for product in products if product.visible
    ]
    in_stock = [
        product for product in visible_products if product.in_stock
    ]
    best_seller = [
        product for product in visible_products if product.best_seller
    ]
    special_offer = [
        product for product in visible_products if product.special_offer
    ]
    featured = [
        product for product in visible_products if product.featured
    ]
    just_arrived = [
        product for product in visible_products if product.just_arrived
    ]
    just_arrived2 = sorted(just_arrived, key=lambda p: p.id, reverse=True)

    # Deal of the week product
    now = timezone.now()
    deal_product = next(
        (
            product for product in visible_products
            if product.deal_of_the_week
            and product.deal_start_date <= now
            and product.deal_end_date >= now
        ),
        None,
    )

    # Fetch other data
    blog_categories = BlogCategory.objects.all().order_by("-created_at")
    blog_posts = Post.objects.all().order_by("-created_at")
    categories = Category.objects.all().order_by("-id")
    banners = Banner.objects.all().order_by("-created_at")
    min_max_price = Product.objects.aggregate(Min("price"), Max("price"))

    # Wishlist handling
    try:
        wishlist = WishList.objects.filter(user=request.user)
    except Exception:
        wishlist = 0

    # Return the context dictionary
    return {
        "in_stock": in_stock,
        "best_seller": best_seller,
        "special_offer": special_offer,
        "featured": featured,
        "top_categories": categories,
        "just_arrived": just_arrived,
        "just_arrived2": just_arrived2,
        "all_products": visible_products,
        "min_max_price": min_max_price,
        "blog_categories": blog_categories,
        "blog_posts": blog_posts,
        "banners": banners,
        "wishlist": wishlist,
        "deal_product": deal_product,
    }


def products_by_category(request):
    category_id = request.GET.get(
        "category_id",
    )  # Assuming the category_id is passed in the query parameters
    products = []
    if category_id:
        products = Product.objects.filter(category__id=category_id)
    return {"filtered_products": products}


def purchased_products_url(request):
    """
    Add the purchased products URL to the context for authenticated users.
    """
    if request.user.is_authenticated:
        return {
            "purchased_product_url": request.build_absolute_uri(
                reverse("ecommerce:purchased_products")
            )
        }
    return {"purchased_product_url": None}
