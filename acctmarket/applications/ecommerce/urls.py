from django.urls import path

from acctmarket.applications.ecommerce import views

app_name = "ecommerce"
urlpatterns = [
    path(
        "add-product", views.AddProductView.as_view(),
        name="add_product"
    ),
    path(
        "add-category", views.AddCategoryView.as_view(),
        name="add_category"
    ),
    path(
        "list-category", views.ListCategoryView.as_view(),
        name="list_category"
    ),
    path(
        "edit-category/<slug:pk>/",
        views.EditCategoryView.as_view(),
        name="edit_category",
    ),
    path(
        "delete-category/<slug:pk>/",
        views.DeleteCategoryView.as_view(),
        name="delete_category",
    ),
    path(
        "list-product", views.ListProductView.as_view(),
        name="list_product"
    ),
    path(
        "edit-product/<slug:pk>/",
        views.EditProductView.as_view(),
        name="edit_product",
    ),
    path(
        "delete-product/<slug:pk>/",
        views.DeleteProductView.as_view(),
        name="delete_product",
    ),
    path(
        "product-detail/<slug:pk>/",
        views.ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "create-product-image",
        views.ProductImagesCreateView.as_view(),
        name="create_product_image",
    ),
    path(
        "list-product-image",
        views.ListProductImages.as_view(),
        name="list_product_images",
    ),
    path(
        "update-product-image/<slug:pk>/",
        views.UpdateProductImages.as_view(),
        name="update_product_image",
    ),
    path(
        "delete-product-image/<slug:pk>/",
        views.DeleteProductImages.as_view(),
        name="delete_product_image",
    ),
    path(
        "product/<slug:pk>/add-review/",
        views.AddReviewsView.as_view(),
        name="add_review",
    ),
    path(
        "add-to-cart/", views.AddToCartView.as_view(),
        name="add_to_cart"
    ),
    path("cart", views.CartListView.as_view(), name="cart_list"),
    path(
        "delete-from-cart",
        views.DeleteFromCartView.as_view(),
        name="delete_from_cart_list",
    ),
    path(
        "update-to-cart",
        views.UpdateCartView.as_view(),
        name="delete_from_cart_list",
    ),

    path(
        "checkout", views.CheckoutView.as_view(),
        name="checkout"
    ),
    path(
        "proceed-payment", views.ProceedPayment.as_view(),
        name="proceed_payment"
    ),
    path(
        "payment-complete/",
        views.PaymentCompleteView.as_view(),
        name="payment_complete",
    ),
    path(
        "payment-failed",
        views.PaymentFailedView.as_view(),
        name="payment_failed",
    ),
    path(
        "wish-lists",
        views.WishlistListView.as_view(),
        name="wishlists",
    ),
    path(
        "add-to-wishlist",
        views.AddToWishlistView.as_view(),
        name="add_to_wishlist",
    ),
    path(
        "verify-payment/<str:reference>/",
        views.VerifyPaymentView.as_view(),
        name="verify_payment",
    ),
    path(
        "initiate-payment/<slug:order_id>/",
        views.InitiatePaystackPaymentView.as_view(),
        name="initiate_payment",
    ),
    path(
        "initiate-flutterwave-payment/<slug:order_id>/",
        views.InitiateFlutterwavePaymentView.as_view(),
        name="initiate_flutterwave_payment"

    ),
    path(
        "handle-flutter-wave-payment",
        views.HandleFlutterwavePaymentView.as_view(),
        name="handle_flutterwave_payment"
    ),
    path(
        "purchased-product",
        views.PurchasedProductsView.as_view(),
        name="purchased_products",
    ),
    path(
        "create_nowpayment/<slug:order_id>/",
        views.NowPaymentView.as_view(),
        name="create_nowpayment",
    ),
    path(
        "verify/nowpayment/<str:reference>/",
        views.VerifyNowPaymentView.as_view(),
        name="verify_nowpayment"
    ),
    path(
        "done-payment/<slug:order_id>/",
        views.DonePaymentView.as_view(),
        name="done_payment"
    ),
    path("ipn/", views.IPNView.as_view(), name="ipn"),


    # https://www.acctmarket.com/ecommerce/webhooks/flutterwave/
    path(
        "webhooks/flutterwave/",
        views.FlutterwaveWebhookView.as_view(),
        name="flutterwave_webhook"
        ),
    path(
         "wallet-payment/", views.WalletPaymentView.as_view(),
         name="wallet_payment"
        ),
    path(
            "apply-coupon/", views.ApplyCouponView.as_view(),
            name="apply_coupon"
        ),

]
