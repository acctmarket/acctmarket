from django.urls import path

from acctmarket.applications.home import views

app_name = "homeapp"
urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("shop", views.ProductShopListView.as_view(), name="shop_list"),
    path(
        "products/<slug:category_slug>/",
        views.ProductsCategoryList.as_view(),
        name="category_list",
    ),
    path(
        "product/<str:pk>/",
        views.ProductShopDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "product-tags/<slug:tag_slug>/",
        views.ProductTagsList.as_view(),
        name="tag_list",
    ),
    path("search", views.ProductSearchView.as_view(),
         name="search"),
    path(
        "filter-product/", views.ProductFilterView.as_view(),
        name="filter_product"
    ),
    path(
        "dashboard", views.DashboardView.as_view(),
        name="dashboard"
    ),
    path(
        "order-details/<int:pk>/", views.OrderDetails.as_view(),
        name="order_details"
    ),
    path(
        "term-policy", views.TermsPolicy.as_view(),
        name="termspolicy"
    ),
    path(
        "contact-us", views.ContactPage.as_view(),
        name="contact_us"
    ),
    path(
        "contact-success", views.ContactSuccessPage.as_view(),
        name="contact_success"
    )
]
