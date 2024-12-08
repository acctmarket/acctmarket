import json
import logging
import os
from decimal import Decimal

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail  # noqa
from django.db import transaction
# from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (CreateView, DeleteView, FormView, ListView,
                                  TemplateView, UpdateView, View)

from acctmarket.applications.ecommerce.forms import (CategoryForm, ProductForm,
                                                     ProductImagesForm,
                                                     ProductKeyFormSet,
                                                     ProductReviewForm)
from acctmarket.applications.ecommerce.models import (CartOrder,
                                                      CartOrderItems, Category,
                                                      Coupon, Payment, Product,
                                                      ProductImages,
                                                      ProductReview, WishList)
from acctmarket.applications.refer.models import (Notification, Wallet,
                                                  WalletTransaction)
from acctmarket.utils.choices import ProductStatus, WalletTransactionTypeChoice
from acctmarket.utils.coupon_discount import (calculate_discount,
                                              validate_coupon)
from acctmarket.utils.mixins import (ContentManagerRequiredMixin,
                                     InitiatePaymentBaseView,
                                     PaymentVerificationMixin)
from acctmarket.utils.payments import NowPayment

logger = logging.getLogger(__name__)


class AddCategoryView(ContentManagerRequiredMixin, CreateView):
    """
    A view for adding a new category.
    """

    model = Category
    form_class = CategoryForm
    template_name = "pages/ecommerce/add_category.html"
    success_url = reverse_lazy("ecommerce:list_category")


class ListCategoryView(ContentManagerRequiredMixin, ListView):
    """
    A view for listing all categories.
    """

    model = Category
    template_name = "pages/ecommerce/category_list.html"
    paginate_by = 10

    def get_queryset(self):
        return Category.objects.annotate(
            total_products=Count("product")).order_by(
            "-created_at",
        )


class EditCategoryView(ContentManagerRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "pages/ecommerce/add_category.html"
    success_url = reverse_lazy("ecommerce:list_category")


class DeleteCategoryView(ContentManagerRequiredMixin, DeleteView):
    model = Category
    template_name = "pages/ecommerce/delete_category.html"
    success_url = reverse_lazy("ecommerce:list_category")


# ---------------------- Category views ends here ----------------


class ProductImagesCreateView(ContentManagerRequiredMixin, FormView):
    template_name = "pages/ecommerce/create_product_image.html"
    form_class = ProductImagesForm
    success_url = reverse_lazy("ecommerce:list_product_images")

    def form_valid(self, form):
        product = form.cleaned_data["product"]
        for each in self.request.FILES.getlist("image"):
            ProductImages.objects.create(image=each, product=product)
        return super().form_valid(form)


class ListProductImages(ContentManagerRequiredMixin, ListView):
    model = ProductImages
    template_name = "pages/ecommerce/list_product_imges.html"
    paginate_by = 10


class UpdateProductImages(ContentManagerRequiredMixin, UpdateView):
    model = ProductImages
    form_class = ProductImagesForm  # Use form_class instead of forms
    template_name = "pages/ecommerce/create_product_image.html"
    success_url = reverse_lazy("ecommerce:list_product_images")

    def form_valid(self, form):
        product = form.cleaned_data["product"]
        images = self.request.FILES.getlist("image")
        for image in images:
            ProductImages.objects.create(product=product, image=image)
        return super().form_valid(form)


class DeleteProductImages(ContentManagerRequiredMixin, DeleteView):
    model = ProductImages
    template_name = "pages/ecommerce/delete_product_image.html"
    success_url = reverse_lazy("ecommerce:list_product_images")


class ListProductView(ContentManagerRequiredMixin, ListView):
    """
    A view for listing all products.
    """

    model = Product
    template_name = "pages/ecommerce/product_list.html"
    paginate_by = 10


class AddProductView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "pages/ecommerce/add_product.html"
    success_url = reverse_lazy("ecommerce:list_product")

    def form_valid(self, form):
        """
        Handle the valid form submission by saving the product
        and the associated product keys.
        """
        response = super().form_valid(form)

        # Initialize the formset with the current product instance
        key_formset = ProductKeyFormSet(
            self.request.POST, instance=self.object)

        if key_formset.is_valid():
            key_formset.save()
            messages.success(
                self.request,
                "Product and product keys successfully added."
            )
        else:
            # Handle formset invalid scenario
            messages.error(
                self.request,
                "There was an issue saving the product keys. Please correct the errors."   # noqa
            )

            return self.form_invalid(form)

        return response

    def form_invalid(self, form):
        """
        Handle the invalid form submission (either main form or formset).
        """
        messages.error(
            self.request,
            "There was an issue with the form. Please check your inputs."
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """
        Add formset to context for rendering in template.
        """
        context = super().get_context_data(**kwargs)
        # Add formset to context for the template
        if self.request.POST:
            context["key_formset"] = ProductKeyFormSet(self.request.POST)
        else:
            context["key_formset"] = ProductKeyFormSet()

        return context


class EditProductView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "pages/ecommerce/add_product.html"
    success_url = reverse_lazy("ecommerce:list_product")

    def form_valid(self, form):
        response = super().form_valid(form)
        key_formset = ProductKeyFormSet(
            self.request.POST, instance=self.object
        )
        if key_formset.is_valid():
            key_formset.save()
        else:
            return self.form_invalid(form)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["key_formset"] = ProductKeyFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["key_formset"] = ProductKeyFormSet(
                instance=self.object)
        return context


class DeleteProductView(ContentManagerRequiredMixin, DeleteView):
    """
    A view for deleting an existing product.
    """

    model = Product
    template_name = "pages/ecommerce/delete_product.html"
    success_url = reverse_lazy("ecommerce:list_product")


class ProductDetailView(ContentManagerRequiredMixin, ListView):
    """
    A view for listing all products.
    """

    model = Product
    template_name = "ecommerce/product_detail.html"


# ---------------------------  ----------------------------------
# ---------------------- Product views ends here ----------------


class AddReviewsView(LoginRequiredMixin, CreateView):
    model = ProductReview
    form_class = ProductReviewForm

    def form_valid(self, form):
        """
        Saves the form data and returns a JSON response containing
        the user"s username,
        the review text, the rating,
        and the average rating for the product.

        Parameters:
            form (ProductReviewForm): The form containing the review data.

        Returns:
            JsonResponse: A JSON response containing the following keys:
                - bool (bool): True if the form is valid, False otherwise.
                - context (dict): A dictionary containing the user"s username,
                  the review text, and the rating.
                - average_review (dict): A dictionary containing the
                average rating for
                the product.

        Raises:
            Product.DoesNotExist: If the product with the
            given primary key does not exist.
        """

        # Check if the user is authenticated and if the user has
        # added a review already
        product = form.instance.product

        form.instance.user = self.request.user
        form.instance.product = Product.objects.get(pk=self.kwargs["pk"])
        self.object = form.save()

        average_review = ProductReview.objects.filter(product=product).aggregate(   # noqa
            rating=Avg("rating"),
        )

        context = {
            "user": self.request.user.name,
            "review": form.instance.review,
            "rating": form.instance.rating,
        }

        return JsonResponse(
            {
                "bool": True,
                "context": context,
                "average_review": average_review,
            },
        )

    def form_invalid(self, form):
        return JsonResponse(
            {
                "bool": False,
                "errors": form.errors,
            },
        )


# ---------------------------  ----------------------------------
# ---------------------- Add reviews ends here ----------------


class AddToCartView(View):
    def get(self, request, *args, **kwargs):
        """
        Adds a product to the cart session data.

        Parameters:
            request (HttpRequest): The HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            JsonResponse: A JSON response containing the updated cart
            data and the total number of items in the cart.

        Description:
            This function is used to add a product to the cart session data.
            It takes the request object as a parameter,
            along with any additional arguments and keyword arguments.
            The function retrieves the product details from the request
            GET parameters
            and creates a dictionary representation of the product.
            It then checks if there is already a cart data object
            in the session.
            If there is, it updates the quantity of the product
            if it already exists in the cart, otherwise
            it adds the product to the cart data. Finally,
            it returns a JSON response containing the updated
            cart data and the total number of items in the cart.
        """

        cart_product = {
            str(request.GET.get("id")): {
                "title": request.GET.get("title"),
                "quantity": request.GET.get("qty"),
                "price": request.GET.get("price"),
                "image": request.GET.get("image"),
                "pid": request.GET.get("id"),
            },
        }

        logger.debug("Request data: %s", request.GET)
        logger.debug("ProductsID (pid): %s", request.GET.get("product_id"))

        if "cart_data_obj" in request.session:
            cart_data = request.session["cart_data_obj"]
            product_id = str(request.GET.get("id"))
            if product_id in cart_data:
                cart_data[product_id]["quantity"] = int(
                    cart_product[product_id]["quantity"],
                )
            else:
                cart_data.update(cart_product)
            request.session["cart_data_obj"] = cart_data
        else:
            request.session["cart_data_obj"] = cart_product

        return JsonResponse(
            {
                "data": request.session["cart_data_obj"],
                "totalcartitems": len(request.session["cart_data_obj"]),
            },
        )


# ---------------------------  ----------------------------------
# ---------------------- Add to cart  ends here ----------------


class CartListView(TemplateView):
    """
    A view that displays the cart items and calculates the total amount.

    This view retrieves the cart data from the session and calculates
    the total amount
    based on the quantity and price of each item in the cart. It then renders
      the
    "pages/ecommerce/cart_list.html" template, passing the cart data, total
    cart items,
    and total amount as context variables.
    """

    template_name = "pages/ecommerce/cart_list.html"

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and checks if the cart is empty.
        Redirects to the home page with a warning message if the cart is empty.
        """
        if (
            "cart_data_obj" not in request.session
            or not request.session["cart_data_obj"]
        ):
            messages.warning(
                request, "Your cart is empty add products to your cart."
            )
            return redirect("homeapp:shop_list")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Retrieves the context data for the view.

        Parameters:
            **kwargs (dict): Additional keyword arguments.

        Returns:
            dict: The context data containing the following keys:
                - cart_data (dict): The cart data stored in the session.
                - totalcartitems (int): The total number of items in the cart.
                - cart_total_amount (float): The total amount of the items
                in the cart.
        """
        context = super().get_context_data(**kwargs)
        cart_total_amount = 0
        cart_data = self.request.session["cart_data_obj"]

        for product_id, item in cart_data.items():
            cart_total_amount += int(item["quantity"]) * float(item["price"])

        context["cart_data"] = cart_data
        context["totalcartitems"] = len(cart_data)
        context["cart_total_amount"] = cart_total_amount

        return context


# ---------------------------  ----------------------------------
# ---------------------- Cart List  ends here ----------------


class DeleteFromCartView(View):
    """
    View to handle removing a product from the
    user's shopping cart.
    The cart is stored in the session, and the item is removed
    based on its product_id.
    After removing the item, it calculates the total price
    of the remaining cart items and returns
    the updated cart data as a JSON response.
    """
    def get(self, request, *args, **kwargs):
        """
        Handles the GET request to remove an item from the cart.
        It retrieves the product_id from the request and removes
        the item from the session-based cart.
        It also calculates the total cart amount
        and renders the updated cart content.
        """

        # Get the product ID from the request
        product_id = str(request.GET.get("id"))
        # Remove the item from the cart
        self.remove_item_from_cart(request, product_id)
        # Calculate the updated cart total amount
        cart_total_amount = self.calculate_cart_total(request)

        context = render_to_string(
            "pages/async/cart_list.html",
            {
                "cart_data": request.session.get("cart_data_obj", {}),
                "totalcartitems": len(request.session.get(
                    "cart_data_obj", {})),
                "cart_total_amount": cart_total_amount,
            },
        )
        # Return the updated cart content and the
        # total number of items as a JSON response
        return JsonResponse(
            {
                "data": context,
                "totalcartitems": len(request.session.get(
                    "cart_data_obj", {})),
            },
        )

    def remove_item_from_cart(self, request, product_id):
        """
        Removes a specific item from the cart stored in the session.
        If the product exists in the cart,
        it deletes the product from the cart.
        """
        if "cart_data_obj" in request.session:
            cart_data = request.session["cart_data_obj"]
            # Remove the product from the cart
            if product_id in cart_data:
                del cart_data[product_id]
                # Save the updated cart to the session
                request.session["cart_data_obj"] = cart_data

    def calculate_cart_total(self, request):
        """
        Calculates the total amount of the cart
        based on the items and their quantities.
        Returns the total cart amount as a float.
        """
        cart_total_amount = 0
        if "cart_data_obj" in request.session:
            for item in request.session["cart_data_obj"].values():
                # Multiply quantity by price for each item
                # and add to the total cart amount
                cart_total_amount += int(
                    item["quantity"]) * float(item["price"])
        return cart_total_amount


# ---------------------------  ----------------------------------
# ---------------------- Delete from cart  ends here ----------------


class UpdateCartView(View):
    """
    View to handle updating the quantity of a product
    in the user's shopping cart.
    The cart is stored in the session,
    and the quantity of an item is updated based on
    the given product_id.
    After updating the quantity, it calculates the total price
    of the cart and returns the updated data as a JSON response.
    """
    def get(self, request, *args, **kwargs):
        """
        Handles the GET request to update the quantity
        of an item in the cart.
        It retrieves the product_id and the new quantity
        from the request and updates the item in the cart.
        It also calculates the updated total cart
        amount and renders the updated cart content.
        """
        # Get the product ID from the request
        product_id = str(request.GET.get("id"))
        # Get the new quantity for the product (default to 1)
        new_quantity = int(request.GET.get("quantity", 1))
        self.update_item_in_cart(request, product_id, new_quantity)
        # Calculate the updated cart total amount
        cart_total_amount = self.calculate_cart_total(request)

        context = render_to_string(
            "pages/async/cart_list.html",
            {
                "cart_data": request.session.get("cart_data_obj", {}),
                "totalcartitems": len(request.session.get(
                    "cart_data_obj", {})),
                "cart_total_amount": cart_total_amount,
            },
        )
        # Return the updated cart content
        # and the total number of items as a JSON response
        return JsonResponse(
            {
                "data": context,
                "totalcartitems": len(request.session.get(
                    "cart_data_obj", {})),
            },
        )

    def update_item_in_cart(self, request, product_id, new_quantity):
        if "cart_data_obj" in request.session:
            cart_data = request.session["cart_data_obj"]
            if product_id in cart_data:
                cart_data[product_id]["quantity"] = new_quantity
                request.session["cart_data_obj"] = cart_data

    def calculate_cart_total(self, request):
        cart_total_amount = 0
        if "cart_data_obj" in request.session:
            for item in request.session["cart_data_obj"].values():
                cart_total_amount += int(
                    item["quantity"]) * float(item["price"])
        return cart_total_amount


# ---------------------------  ----------------------------------
# ---------------------- Update Cart  ends here ----------------


class CheckoutView(LoginRequiredMixin, TemplateView):
    """
    A view for the checkout process, including applying discounts and
    handling wallet payment validation.
    """
    template_name = "pages/ecommerce/checkout.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cart_data = self.request.session.get("cart_data_obj", {})
        if not cart_data:
            messages.error(self.request, "Your cart is empty.")
            return redirect("ecommerce:cart_list")

        # Calculate the total cart amount
        cart_total_amount = sum(
            Decimal(item["price"]) * int(item["quantity"]) for item in cart_data.values()  # noqa
        )

        # Coupon logic
        applied_coupon_code = self.request.session.get("applied_coupon")
        discount = Decimal("0.00")
        coupon_message = None  # Message to display on the front-end

        # Check if any valid coupons exist in the database
        valid_coupons = Coupon.objects.filter(
            Q(valid_from__lte=timezone.now().date()) &
            Q(valid_to__gte=timezone.now().date()) &
            Q(times_used__lt=F('usage_limit'))
        )

        # Set whether there are any valid coupons
        show_coupon_form = valid_coupons.exists()

        if applied_coupon_code:
            try:
                coupon = Coupon.objects.get(code=applied_coupon_code)
                if coupon.is_valid():
                    discount = calculate_discount(coupon, cart_data)
                    coupon_message = f"Coupon '{applied_coupon_code}' applied successfully!" # noqa
                else:
                    messages.error(self.request, "The applied coupon is no longer valid.")  # noqa
                    del self.request.session["applied_coupon"]
            except ObjectDoesNotExist:
                messages.error(self.request, "Invalid coupon. Removing it from your session.")  # noqa
                del self.request.session["applied_coupon"]

        # Update cart total after applying the discount
        cart_total_amount -= discount

        wallet = get_object_or_404(Wallet, user=self.request.user)
        wallet_balance = wallet.balance
        can_pay_with_wallet = wallet_balance >= cart_total_amount

        # Create order and payment (unchanged from your original code)
        with transaction.atomic():
            try:
                order = CartOrder.objects.create(
                    user=self.request.user,
                    price=cart_total_amount,
                    paid_status=False,
                    payment_method="wallet",
                )

                payment = Payment.objects.create(
                    order=order,
                    amount=cart_total_amount,
                    wallet=wallet,
                    status="pending",
                    user=self.request.user,
                )

                order_items = [
                    CartOrderItems(
                        order=order,
                        product=get_object_or_404(Product, id=product_id),
                        invoice_no=f"INVOICE_NO_{order.id}",
                        quantity=int(item["quantity"]),
                        price=Decimal(item["price"]),
                        total=Decimal(item["price"]) * int(item["quantity"]),
                    )
                    for product_id, item in cart_data.items()
                ]
                CartOrderItems.objects.bulk_create(order_items)

                self.request.session['order_id'] = order.id
                self.request.session['payment_id'] = payment.id

            except Exception as e:
                logging.error(f"Error during checkout: {e}")
                messages.error(self.request, "An error occurred during checkout.")  # noqa
                return redirect("ecommerce:cart_list")

        # Update context with necessary data
        context.update({
            "user_name": self.request.user.name,
            "user_email": self.request.user.email,
            "cart_data": cart_data,
            "cart_total_amount": cart_total_amount,
            "discount": discount,
            "order_id": order.id,
            "payment_id": payment.id,
            "wallet_balance": wallet_balance,
            "can_pay_with_wallet": can_pay_with_wallet,
            "coupon_message": coupon_message,  # Include coupon message
            "show_coupon_form": show_coupon_form,
        })

        return context


class ApplyCouponView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        coupon_code = request.POST.get("coupon_code")
        cart_data = self.request.session.get("cart_data_obj", {})

        if not cart_data:
            messages.error(self.request, "Your cart is empty.")
            return redirect("ecommerce:checkout")

        coupon, error_message = validate_coupon(coupon_code, cart_data)
        if coupon:
            request.session["applied_coupon"] = coupon_code
            messages.success(request, f"Coupon '{coupon_code}' applied successfully!")  # noqa
        else:
            messages.error(request, error_message)

        return redirect("ecommerce:checkout")


class WalletPaymentView(PaymentVerificationMixin, View):
    """
    View to display wallet payment confirmation and handle the payment.
    """
    template_name = "pages/ecommerce/wallet_payment_confirmation.html"

    def get(self, request, *args, **kwargs):
        # Retrieve payment and order information from session
        payment_id = request.session.get('payment_id')
        if not payment_id:
            messages.error(request, "Payment information is missing.")
            return redirect("ecommerce:checkout")

        payment = get_object_or_404(Payment, id=payment_id)
        order = payment.order

        # Check if wallet balance is sufficient
        if payment.wallet.balance < payment.amount:
            messages.error(request, "Insufficient wallet balance.")
            return redirect("ecommerce:checkout")

        # Pass order and payment details to the template for confirmation
        context = {
            "order": order,
            "payment": payment,
            "wallet_balance": payment.wallet.balance,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Retrieve payment ID from session
        payment_id = request.session.get('payment_id')
        if not payment_id:
            messages.error(request, "Payment information is missing.")
            return redirect("ecommerce:checkout")

        payment = get_object_or_404(Payment, id=payment_id)

        try:
            with transaction.atomic():
                # Verify wallet payment
                if payment.verify_wallet_payment(request):

                    # Record the transaction (debit)
                    wallet = payment.wallet
                    WalletTransaction.record_transaction(
                        wallet, payment.amount,
                        WalletTransactionTypeChoice.DEBIT)

                    # Update the CartOrder's paid status
                    order: CartOrder = payment.order
                    order.paid_status = True
                    order.product_status = ProductStatus.DELIVERED
                    order.save()

                    # Trigger key assignment, notification,
                    # and redirect on success
                    return self.assign_keys_and_notify(request, payment)

                else:
                    messages.error(
                        request,
                        "Wallet verification failed. Please check your wallet balance or try again."  # noqa
                    )
                    return redirect("ecommerce:payment_failed")

        except Exception as e:
            logging.error(f"Wallet payment processing error: {e}")
            messages.error(
                request,
                "An error occurred while processing your payment."
            )
            return redirect("ecommerce:payment_failed")


class ProceedPayment(LoginRequiredMixin, TemplateView):
    template_name = "pages/ecommerce/checkout.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_data = self.request.session.get(
            "cart_data_obj",
            {},
        )  # Fetch cart data from session

        # Calculate total cart amount
        cart_total_amount = sum(
            Decimal(item["price"]) * int(item["quantity"])
            for item in cart_data.values()
        )

        # Create an order in the database
        order = CartOrder.objects.create(
            user=self.request.user,
            price=cart_total_amount,
            paid_status=False,
        )

        # Create order items in the database
        order_items = [
            CartOrderItems(
                order=order,
                product=get_object_or_404(Product, id=product_id),
                invoice_no=f"INVOICE_NO_{order.id}",
                quantity=int(item["quantity"]),
                price=Decimal(item["price"]),
                total=Decimal(item["price"]) * int(item["quantity"]),
            )
            for product_id, item in cart_data.items()
        ]

        CartOrderItems.objects.bulk_create(order_items)

        user = self.request.user
        # Update context with necessary data
        context.update(
            {
                "user_name": user.name,
                "user_email": user.email,
                "user_country": user.country,
                "user_phone": user.phone_no,
                "cart_data": cart_data,
                "totalcartitems": len(cart_data),
                "cart_total_amount": cart_total_amount,
                "order_price": order.price,
                "order_id": order.id,
            },
        )

        return context

    # Overriding the get method to redirect to initiate paystack payment
    # def get(self, request, *args, **kwargs):
    #     context = self.get_context_data(**kwargs)
    #     return redirect("ecommerce:initiate_payment",
    #                     order_id=context["order_id"])
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return redirect("ecommerce:initiate_flutterwave_payment",
                        order_id=context["order_id"])


class InitiatePaystackPaymentView(InitiatePaymentBaseView):
    payment_method = "paystack"
    template_name = "pages/ecommerce/initiate_payment.html"

    def initiate_payment(self, request, payment, amount_in_naira):
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "email": request.user.email,
            "amount": int(amount_in_naira * 100),  # Amount in kobo
            "reference": payment.reference,
            "callback_url": request.build_absolute_uri(
                reverse("ecommerce:verify_payment", args=[payment.reference]),
            ),
        }

        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers=headers,
            json=data,
        )
        response_data = response.json()

        if response_data.get("status") is True:
            authorization_url = response_data["data"]["authorization_url"]
            return redirect(authorization_url)
        else:
            messages.error(
                request, f"Error initializing payment: {response_data.get('message', 'Unknown error')}",   # noqa
            )
            return redirect("ecommerce:checkout")


class InitiateFlutterwavePaymentView(InitiatePaymentBaseView):
    payment_method = "flutterwave"
    template_name = "pages/ecommerce/initiate_payment.html"

    def initiate_payment(self, request, payment, amount_in_naira):
        """
        Prepares the context dictionary for rendering
        the Flutterwave payment initiation.
        """
        logging.info(f"Initiating payment with tx_ref: {payment.reference}")
        logging.info(f"Payment amount: {amount_in_naira} NGN")
        if settings.USE_FLUTTER_WAVE_TESTING:
            flutterwave_public_key = settings.FLUTTERWAVE_PUBLIC_KEY_TEST
        else:
            flutterwave_public_key = settings.FLUTTERWAVE_PUBLIC_KEY

        context = {
            'public_key': flutterwave_public_key,
            'tx_ref': payment.reference,
            'amount': amount_in_naira,
            'currency': "NGN",
            'payment_options': "card, mobilemoneyghana, ussd, banktransfer",   # noqa
            'redirect_url': request.build_absolute_uri(
                reverse('ecommerce:handle_flutterwave_payment')
            ),
            'meta': {
                'consumer_id': payment.order.id,
                'consumer_mac': payment.reference,
            },
            'customer': {
                'email': payment.user.email,
                'phone_number': request.user.phone_no,
                'name': f"{payment.user.email}",
            },
            'customizations': {
                'title': "AcctMarket",
                'description': "Payment for purchased product(s)",
                'logo': request.build_absolute_uri(
                    static('assets/images/logo/logoicon.png')
                ),
            }
        }

        # Pass the context to the template
        return self.render_to_response(context)


class HandleFlutterwavePaymentView(View):
    def get(self, request, *args, **kwargs):
        """
        Handles the response from Flutterwave after payment.
        """
        tx_ref = request.GET.get('tx_ref')
        status = request.GET.get('status')

        if not tx_ref:
            messages.error(request, "Transaction reference not provided.")
            return redirect("ecommerce:checkout")

        try:
            payment = Payment.objects.get(reference=tx_ref)
        except Payment.DoesNotExist:
            messages.error(request, "Payment not found.")
            return redirect("ecommerce:checkout")

        if status == "successful":
            # Redirect to VerifyPaymentView to complete verification   # boqa
            return redirect(reverse(
                'ecommerce:verify_payment',
                args=[payment.reference])
            )
        elif status == "completed":
            # Handle pending payments (e.g., bank transfers)
            messages.info(
                request,
                "Your transfer payment still processing. Please wait for confirmation."  # noqa
            )
            return redirect("ecommerce:checkout")
        else:
            messages.error(request, f"Payment was not successful. {status}")
            return redirect("ecommerce:checkout")


@method_decorator(csrf_exempt, name='dispatch')
class FlutterwaveWebhookView(View, PaymentVerificationMixin):
    def post(self, request, *args, **kwargs):
        """
        Handles Flutterwave webhook notifications for payment status updates.
        """
        # Step 1: Verify the request
        if not self.verify_webhook(request):
            # Unauthorized if verification fails
            return HttpResponse(status=401)

        # Step 2: Parse the incoming webhook data
        try:
            data = json.loads(request.body)
            tx_ref = data["data"]["tx_ref"]
            status = data["data"]["status"]
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error parsing webhook data: {e}")
            return JsonResponse(
                {
                    "status": "error", "message": "Invalid payload"
                }, status=400
            )

        # Step 3: Look for the Payment instance by transaction reference (tx_ref)  # noqa
        payment = get_object_or_404(Payment, reference=tx_ref)
        logging.info(f"Processing payment for tx_ref: {tx_ref}, status: {status}")  # noqa

        # Step 4: Handle payment status
        if status == "successful":
            # Reuse existing method
            return self.assign_keys_and_notify(payment)
        elif status == "pending":
            return self.handle_pending_payment(payment)
        elif status == "failed":
            return self.handle_failed_payment(payment)
        else:
            return JsonResponse(
                {
                    "status": "error", "message": "Unknown status received"
                }, status=400
            )

    def verify_webhook(self, request):
        """
        Verifies the webhook request from Flutterwave using the secret hash.
        """
        secret_hash = os.getenv("FLW_SECRET_HASH")
        signature = request.headers.get("verif-hash")

        if not signature or signature != secret_hash:
            logging.warning(
                "Invalid or missing verif-hash in Flutterwave webhook"
            )
            return False

        return True

    def handle_pending_payment(self, payment):
        payment.status = "pending"
        payment.save()
        messages.info(
            None,
            "Payment is pending, we will notify you once it's confirmed."
        )
        return JsonResponse(
            {"status": "pending", "message": "Payment is pending."},
            status=200
        )

    def handle_failed_payment(self, payment):
        payment.status = "failed"
        payment.save()
        messages.error(None, "Payment failed, please try again.")
        return JsonResponse(
            {
                "status": "failed", "message": "Payment failed."
            }, status=200
        )


class VerifyPaymentView(View, PaymentVerificationMixin):
    """
    This view handles the payment verification
    for Paystack, Flutterwave, and NowPayments.
    Once payment is verified, it assigns product keys and notifies the user.
    """
    def get(self, request, reference, *args, **kwargs):
        """
        Handles payment verification based on the payment method.
        """
        logging.info(f"Received callback for tx_ref: {reference}")
        payment = get_object_or_404(Payment, reference=reference)
        logging.info(f"Expected tx_ref: {payment.reference}")
        verified = False

        if payment.order.payment_method == "paystack":
            verified = payment.verify_paystack_payment()
        elif payment.order.payment_method == "nowpayments":
            verified = payment.verify_payment_nowpayments(request)
        elif payment.order.payment_method == "flutterwave":
            verified = payment.verify_flutterwave_payment()
        else:
            messages.error(request, "Unknown payment method")
            return redirect("ecommerce:payment_failed")

        if verified:
            return self.assign_keys_and_notify(request, payment)
        else:
            messages.error(request, "Verification failed no flutter")
            return redirect("ecommerce:payment_failed")


class VerifyNowPaymentView(View, PaymentVerificationMixin):
    def complete_payment(self, request, payment):
        # Proceed to complete the payment and assign keys
        return self.assign_keys_and_notify(request, payment)

    def verify_and_process_payment(self, request, reference):
        payment = get_object_or_404(Payment, reference=reference)

        # Check if payment is already successful
        if payment.status == "successful" and payment.verified:
            messages.warning(
                request,
                "Payment is already successful and verified."
            )
            return self.complete_payment(request, payment)

        # Attempt to verify with NowPayments
        nowpayment = NowPayment()
        success, result = nowpayment.verify_payment(int(payment.payment_id))

        if success and result.get("payment_status") == "confirmed":
            payment.status = "verified"
            payment.verified = True
            payment.save()

            # Complete the payment by assigning keys and sending emails
            return self.complete_payment(request, payment)
        else:
            payment.status = "failed"
            payment.save()
            messages.error(request, "Verification failed.")
            return redirect("ecommerce:payment_failed")

    def get(self, request, reference):
        return self.verify_and_process_payment(request, reference)

    def post(self, request, reference):
        return self.verify_and_process_payment(request, reference)


class DonePaymentView(View, PaymentVerificationMixin):
    def post(self, request, *args, **kwargs):
        # Retrieve the order ID from the URL or form data
        order_id = kwargs.get("order_id") or request.POST.get("order_id")
        order = get_object_or_404(CartOrder, id=order_id, user=request.user)

        # Retrieve the Payment object associated with this order
        payment = get_object_or_404(Payment, order=order, user=request.user)

        if order.payment_method == "nowpayments":
            payment.status = "verified"
            payment.verified = True
            payment.save()

            order.paid_status = True
            order.save()

            # Use the method from PaymentVerificationMixin
            # to assign keys and notify
            return self.assign_keys_and_notify(request, payment)

        else:
            messages.error(
                request,
                "Payment has already been verified or is not eligible for completion."  # noqa
            )

        return redirect(
            reverse("ecommerce:payment_complete",
                    kwargs={"order_id": order.id})
        )


class NowPaymentView(View):
    def get_supported_currencies(self):
        """
        Fetch the list of supported currencies from NOWPayments API.
        """
        # Initialize NowPayment to use the correct API URL and key
        nowpayment = NowPayment(
            callback_url_name="ecommerce:ipn",
            success_url_name="ecommerce:payment_complete",
            cancel_url_name="ecommerce:payment_failed"
        )
        # Uses sandbox or live URL based on settings
        url = f"{nowpayment.api_url}/currencies"

        headers = {"x-api-key": nowpayment.api_key}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json().get("currencies", [])
        return []

    def get(self, request, order_id):
        """
        Render the payment page with supported currencies and order details.
        """
        order = get_object_or_404(CartOrder, id=order_id, user=request.user)
        supported_currencies = self.get_supported_currencies()
        return render(
            request,
            "pages/ecommerce/create_nowpayment.html",
            {"supported_currencies": supported_currencies, "order": order},
        )

    def post(self, request, order_id):
        """
        Handle the payment creation request by posting to NOWPayments API.
        """
        order = get_object_or_404(CartOrder, id=order_id, user=request.user)
        pay_currency = request.POST.get("pay_currency")

        # Set the payment method to NOWPayments
        order.payment_method = "nowpayments"
        order.save()

        # Create or get a payment object
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "user": request.user,
                "amount": float(order.price),
                "reference": Payment.generate_unique_reference(),
                "payment_id": Payment.generate_payment_id(),
            },
        )

        # Create a NOWPayments invoice
        nowpayment = NowPayment(
            callback_url_name="ecommerce:ipn",
            success_url_name="ecommerce:payment_complete",
            cancel_url_name="ecommerce:payment_failed"
        )
        payment_response = nowpayment.create_payment(
            amount=float(order.price),
            currency=pay_currency,
            order_id=order.id,
            description=f"Order #{order.id} for user {order.user.id}",
            request=request,
        )

        if payment_response["status"]:
            # Update the payment with the NOWPayments ID
            payment.payment_id = payment_response["data"]["id"]
            payment.save()

            return redirect(payment_response["data"]["invoice_url"])
        else:
            # Handle the error
            messages.error(request, payment_response["message"])
            return redirect("ecommerce:payment_failed")


@method_decorator(csrf_exempt, name="dispatch")
class IPNView(View):
    def post(self, request, *args, **kwargs):
        """
        Handle IPN (Instant Payment Notification)
        from NOWPayments.
        """
        data = json.loads(request.body)
        order_id = data.get("order_id")
        messages.info(
            request,
            f"IPN received for order ID: {order_id}"
        )

        try:
            order = get_object_or_404(CartOrder, id=order_id)
            payment = order.payment

            if not payment:
                messages.error(
                    request,
                    "Payment not found for order."
                )
                return JsonResponse({
                    "status": "error",
                    "message": "Payment not found for order"
                }, status=404)

            verify_payment_view = VerifyNowPaymentView()
            response = verify_payment_view.verify_and_process_payment(
                request, payment.reference
            )

            if response.status_code == 302 and "payment_complete" in response.url:   # noqa
                return JsonResponse({
                    "status": "success",
                    "redirect_url": response.url
                })
            else:
                return JsonResponse({
                    "status": "failed",
                    "redirect_url": response.url
                }, status=400)
        except Exception as e:
            messages.error(request, f"IPN processing error: {e}")
            return JsonResponse({
                "status": "error",
                "message": str(e)}, status=500)


class PaymentCompleteView(LoginRequiredMixin, TemplateView):
    template_name = "pages/ecommerce/payment_complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Retrieve the latest CartOrder for the user
        order = CartOrder.objects.filter(user=user).order_by('-created_at').first()  # noqa

        if order:
            # Retrieve the Payment object associated with this order
            payment = Payment.objects.filter(order=order, user=user).first()

            if payment:
                # Only show verification button if payment is incomplete and
                # via NowPayments
                if order.payment_method.lower() == "nowpayments" and not payment.verified:  # noqa
                    context["show_verification_button"] = True
                    context["done_payment_url"] = reverse(
                        "ecommerce:done_payment",
                        kwargs={"order_id": order.id}
                    )

                # Create a notification for payment success
                if payment.verified:
                    Notification.objects.create(
                        user=user,
                        message=f"Your payment for order #{order.id} has been successfully processed.",  # noqa
                        notification_type='payment_success'
                    )
                    context["payment_status"] = payment.status
                    context["payment_id"] = payment.id

                # Add payment details to context
                context["payment_status"] = payment.status
                context["payment_id"] = payment.id

            # Add order details to context
            context["order"] = order
            context["order_total"] = order.price

            # Clear session data related to the order and payment
            # after successful payment

            if payment and payment.verified:
                if 'order_id' in self.request.session:
                    del self.request.session['order_id']
                if 'payment_id' in self.request.session:
                    del self.request.session['payment_id']

        # Calculate total cart amount from session data
        cart_data_obj = self.request.session.get("cart_data_obj", {})
        cart_total_amount = sum(
            Decimal(item["quantity"]) * Decimal(item["price"]) for item in cart_data_obj.values()  # noqa
        )

        # Add cart details to context
        context.update({
            "cart_data": cart_data_obj,
            "total_cart_items": len(cart_data_obj),
            "cart_total_amount": cart_total_amount,
        })

        # Clear the cart session data upon payment completion
        if 'cart_data_obj' in self.request.session:
            del self.request.session['cart_data_obj']

        return context


class PaymentFailedView(LoginRequiredMixin, TemplateView):
    template_name = "pages/ecommerce/payment_failed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_data_obj = self.request.session.get("cart_data_obj", {})
        context["cart_data"] = cart_data_obj
        context["totalcartitems"] = len(cart_data_obj)
        return context


class PurchasedProductsView(LoginRequiredMixin, ListView):
    template_name = "pages/ecommerce/purchased_products.html"
    context_object_name = "order_items"

    def get_queryset(self):
        return CartOrderItems.objects.filter(
            order__user=self.request.user,
            order__paid_status=True,
        ).select_related("product", "order")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_items = self.get_queryset()

        for item in order_items:
            if not item.transaction_id:
                item.transaction_id = item.generate_transaction_id()
                item.save()

        context["order_items"] = order_items
        return context

    def dispatch(self, request, *args, **kwargs):
        if not CartOrder.objects.filter(
            user=request.user, paid_status=True
        ).exists():
            messages.warning(
                request,
                "Sorry You do not have any purchase yet you can purchase from our shop.")    # noqa
            return redirect("homeapp:shop_list")
        return super().dispatch(request, *args, **kwargs)


class WishlistListView(LoginRequiredMixin, ListView):
    model = WishList
    template_name = "pages/ecommerce/wish_list.html"
    context_object_name = "wishlists"


class AddToWishlistView(View):
    def get(self, request, *args, **kwargs):
        product_id = request.GET.get("id")
        product = get_object_or_404(Product, id=product_id)

        context = {}

        wishlist_count = WishList.objects.filter(
            product=product,
            user=request.user,
        ).count()
        print(wishlist_count)

        if wishlist_count > 0:
            context = {
                "bool": True,
            }
        else:
            WishList.objects.create(
                product=product,
                user=request.user,
            )
            context = {
                "bool": True,
            }

        return JsonResponse(context)
