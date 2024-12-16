import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
# from django.template.loader import render_to_string   # noqa
from django.urls import reverse
from django.views.generic import TemplateView

from acctmarket.applications.ecommerce.models import (CartOrder, Payment,
                                                      ProductKey)
from acctmarket.applications.users.models import (
    ContentManager, CustomerSupportRepresentative)
from acctmarket.utils.payments import convert_to_naira, get_exchange_rate


class ContentManagerRequiredMixin(LoginRequiredMixin):
    """
    A mixin that only allows access to content managers and superusers.
    """

    def dispatch(self, request, *args, **kwargs):
        # Ensure the user is authenticated first
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Check if the user is a content manager or superuser
        if (
            not self.user_is_content_manager(request.user)
            and not request.user.is_superuser
        ):
            return HttpResponseForbidden(
                "You don't have permission to access this page.",
            )
        return super().dispatch(request, *args, **kwargs)

    def user_is_content_manager(self, user):
        """
        Checks if the user is a content manager.
        """
        return ContentManager.objects.filter(user=user).exists()


class CustomerSupportRepresentativemixin(LoginRequiredMixin):
    """
    A mixin that only allows access to customer support representatives.
    """

    def dispatch(self, request, *args, **kwargs):
        # Ensure the user is authenticated first
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Check if the user is a customer support representative
        if not self.user_is_customer_support_representative(request.user):
            return HttpResponseForbidden(
                "You don't have permission to access this page.",
            )
        return super().dispatch(request, *args, **kwargs)

    def user_is_customer_support_representative(self, user):
        """
        Checks if the user is a customer support representative.
        """
        return CustomerSupportRepresentative.objects.filter(user=user).exists()


class PaymentVerificationMixin:
    """
    Mixin class for handling payment verification and post-verification actions
    such as assigning product keys, sending email notifications,
      and handling errors.
    """

    def assign_keys_and_notify(self, request, payment):
        """
        Assigns product keys to the order, sends email notifications,
        and handles any errors.
        """
        try:
            with transaction.atomic():
                # Assign unique keys to the order
                self.assign_unique_keys_to_order(payment.order.id)

                # Send email notification to the user
                self.send_product_access_email(request, payment)

                # Notify the site admin about the purchase
                self.notify_site_owner(request, payment)

                # Notify the user of successful verification
                messages.success(
                    request,
                    "Payment verification successful. Check your email for product access.",  # noqa
                )
                return redirect("ecommerce:payment_complete")
        except Exception as e:
            logging.exception()
            f"Error during key assignment and notification: {e}"
            messages.error(
                request,
                f"Payment verified, but there was an issue: {e}",
            )
            return redirect("ecommerce:payment_failed")

    def assign_unique_keys_to_order(self, order_id):
        """
        Assigns unique product keys to each item
        in the order and updates stock.
        """
        order = get_object_or_404(CartOrder, id=order_id)

        for order_item in order.order_items.all():
            product = order_item.product
            quantity = order_item.quantity

            # Get available unused keys for the product
            available_keys = ProductKey.objects.select_for_update().filter(
                product=product,
                is_used=False,
            )[:quantity]

            if len(available_keys) < quantity:
                # Handle insufficient keys
                self.handle_insufficient_keys(order_item, available_keys)
                continue

            # Assign keys and update stock
            self._assign_keys_and_update_stock(
                order_item,
                available_keys,
                quantity,
            )

    def _assign_keys_and_update_stock(
        self,
        order_item,
        available_keys,
        quantity,
    ):
        """
        Assigns keys to the order item and
        updates the product's stock and visibility.
        """
        keys_and_passwords = []
        for i in range(quantity):
            product_key = available_keys[i]
            product_key.is_used = True
            product_key.save()
            keys_and_passwords.append(
                {
                    "key": product_key.key,
                    "password": product_key.password,
                }
            )

        # Save the assigned keys to the order item
        order_item.keys_and_passwords = keys_and_passwords
        order_item.save()

        # Update product stock and visibility
        product = order_item.product
        product.quantity_in_stock = max(
            0,
            product.quantity_in_stock - quantity,
        )
        product.visible = product.quantity_in_stock > 0
        product.save()

        logging.info(
            f"Stock updated for product '{product.title}': "
            f"{product.quantity_in_stock} items remaining.",
        )

    def send_product_access_email(self, request, payment):
        """
        Sends an email to the user with a link to access purchased products.
        """
        purchased_product_url = request.build_absolute_uri(
            reverse("ecommerce:purchased_products"),
        )
        user_email = payment.order.user.email

        send_mail(
            "Your Purchase is Complete",
            f"Thank you for your purchase. You can access your products here: {purchased_product_url}",  # noqa
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )

    def handle_insufficient_keys(self, order_item, available_keys):
        """
        Handles cases where there are not enough product keys available.
        """
        keys_and_passwords = []
        for key in available_keys:
            key.is_used = True
            key.save()
            keys_and_passwords.append(
                {
                    "key": key.key,
                    "password": key.password,
                }
            )

        order_item.keys_and_passwords = keys_and_passwords
        order_item.save()

        product = order_item.product
        user = order_item.order.user
        self.notify_user_insufficient_keys(user, product)

    def notify_user_insufficient_keys(self, user, product):
        """
        Notifies the user and site admin about insufficient keys for a product.
        """
        message = (
            f"We're sorry, but we do not have enough keys for the product '{product.title}'. "  # noqa
            f"We will contact you shortly."
        )
        send_mail(
            "Insufficient Product Keys",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        admin_message = (
            f"A new purchase was made by {user.username} (User ID: {user.id}, Email: {user.email}) "  # noqa
            f"for the product '{product.title}', but there were insufficient keys to fulfill the order. "  # noqa
            f"Please add more keys to this product and update the user's order accordingly."  # noqa
        )
        send_mail(
            "Action Required: Insufficient Product Keys for New Purchase",
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER],
            fail_silently=False,
        )

    def notify_site_owner(self, request, payment):
        """
        Notifies the site owner about a new order.
        """
        site_owner_email = settings.EMAIL_HOST_USER
        order = payment.order
        user = request.user

        subject = f"New Purchase by {user.username} - Order #{order.id}"
        message = (
            f"User {user.username} has made a new purchase. Order details are attached."  # noqa
        )

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [site_owner_email],
            fail_silently=False,
        )


class InitiatePaymentBaseView(LoginRequiredMixin, TemplateView):
    payment_method = None  # To be defined in the child classes
    template_name = None

    def get(self, request, order_id, *args, **kwargs):
        """
        Retrieves a `CartOrder` object based on the provided
        `order_id` and the user making the request.
        Sets the payment method of the order to "paystack"
        and saves the order.
        Retrieves or creates a `Payment` object associated
        with the order.
        Sends a POST request to the Paystack API
        to initialize a transaction.
        Handles the response from the API and redirects
        the user to the authorization URL if the status is True.
        Otherwise, displays an error message and redirects
        the user to the checkout page.

        Parameters:
            request (HttpRequest): The HTTP request object.
            order_id (int): The ID of the order.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponseRedirect: A redirect to the
            authorization URL if the status is True.
            HttpResponseRedirect: A redirect to the
            checkout page if the status is False.
        """
        order = get_object_or_404(
            CartOrder,
            id=order_id,
            user=request.user,
        )
        order.payment_method = self.payment_method
        order.save()

        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "user": request.user,
                "amount": order.price,
            },
        )

        try:
            exchange_rate = get_exchange_rate()
            amount_in_naira = convert_to_naira(payment.amount, exchange_rate)
        except Exception as e:
            messages.error(request, f"Error fetching exchange rate: {e!s}")
            return redirect("ecommerce:checkout")

        # Call the method that handles the payment gateway specifics
        return self.initiate_payment(request, payment, amount_in_naira)

    def initiate_payment(self, request, payment, amount_in_naira):
        """
        This method should be implemented in child classes.
        It should handle the specifics of each payment gateway.
        """
        raise NotImplementedError(
            "This method should be implemented in a subclass",
        )
