import logging
import uuid
from decimal import Decimal

import auto_prefetch
from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import (CASCADE, SET_NULL, BooleanField, CharField,
                              CheckConstraint, DateField, DateTimeField,
                              DecimalField, F, FileField, IntegerField,
                              JSONField, ManyToManyField, PositiveIntegerField,
                              Q, SlugField, TextField)
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, TaggedItemBase

from acctmarket.utils.choices import (COUPON_CHOICE, ProductStatus, Rating,
                                      Status)
from acctmarket.utils.media import MediaHelper
from acctmarket.utils.models import (ImageTitleTimeBaseModels, TimeBasedModel,
                                     TitleandUIDTimeBasedModel)
from acctmarket.utils.payments import (Flutterwave, NowPayment, PayStack,
                                       convert_to_naira, get_exchange_rate)

# Create your models here.


logger = logging.getLogger(__name__)


class Permissions:
    CAN_CRUD_PRODUCT = Permission.objects.filter(
        codename__in=["add_product", "change_product", "delete_product"],
    )
    CAN_CRUD_CATEGORY = Permission.objects.filter(
        codename__in=["add_category", "change_category", "delete_category"],
    )


class CharUUIDTaggedItem(GenericTaggedItemBase, TaggedItemBase):
    """
    Overiding the tagit manager to use charfield instead of integer
    """

    object_id = CharField(max_length=120, db_index=True)


class Category(ImageTitleTimeBaseModels):
    slug = SlugField(default="", blank=True)
    sub_category = auto_prefetch.ForeignKey(
        "self",
        on_delete=CASCADE,
        blank=True,
        null=True,
        related_name="subcategories",
    )

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        """
        Saves the instance with a slug generated
        from the title if no slug is provided.

        Parameters:
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            None
        """
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# Match your custom PK length


class Product(TitleandUIDTimeBasedModel, ImageTitleTimeBaseModels):
    user = auto_prefetch.ForeignKey(
        "users.User",
        verbose_name=_("User"),
        on_delete=SET_NULL,
        null=True,
    )
    category = auto_prefetch.ForeignKey(
        Category,
        verbose_name=_("Category"),
        on_delete=SET_NULL,
        null=True,
    )
    description = RichTextUploadingField("Description", default="", null=True)
    price = DecimalField(
        max_digits=100,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    oldprice = DecimalField(
        max_digits=100,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    quantity_in_stock = IntegerField(
        blank=True,
        null=True,
        default=0,
    )
    specification = RichTextUploadingField(
        "specification",
        default="",
        null=True,
    )
    product_status = CharField(
        choices=Status.choices,
        default=Status.IN_REVIEW,
        max_length=10,
    )
    tags = TaggableManager(
        through=CharUUIDTaggedItem,
        blank=True,
        help_text="A comma-separated list of tags.",
    )
    in_stock = BooleanField(default=True)
    featured = BooleanField(default=False)
    digital = BooleanField(default=True)
    best_seller = BooleanField(default=False)
    special_offer = BooleanField(default=False)
    just_arrived = BooleanField(default=True)
    deal_of_the_week = BooleanField(default=False)
    deal_start_date = DateTimeField(null=True, blank=True)
    deal_end_date = DateTimeField(null=True, blank=True)
    resource = FileField(
        upload_to=MediaHelper.get_file_upload_path,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name_plural = "Products"
        ordering = ["-created_at", "-updated_at"]
        permissions = [
            ("can_crud_product", "Can create, update, and delete product"),
        ]

    def get_percentage(self, decimal_places=2):
        if self.oldprice > 0:
            percentage = ((self.oldprice - self.price) / self.oldprice) * 100
            return round(percentage, decimal_places)

        return 0

    def get_discount_price(self):
        if self.oldprice > 0:
            return self.oldprice - self.price

    def get_deal_price(self):
        if (
            self.deal_of_the_week
            and self.deal_start_date <= timezone.now() <= self.deal_end_date
        ):
            return self.price * (1 - self.discount_percentage / 100)
        return self.price

    def get_applicable_discount(self):
        """
        Check if any valid coupon applies to this product
        and return the discount info.
        """
        today = timezone.now().date()
        coupons = Coupon.objects.filter(
            Q(universal=True)
            | Q(applicable_products=self)
            | Q(applicable_categories=self.category),
            valid_from__lte=today,
            valid_to__gte=today,
            times_used__lt=F("usage_limit"),
        )
        print(f"Coupons for {self.title}: {coupons}")

        # If no coupon is applicable
        if not coupons.exists():
            return None

        # Get the highest discount (you can modify the logic if needed)
        best_coupon = max(
            coupons,
            key=lambda coupon: (
                coupon.discount_value
                if coupon.discount_type == "flat"
                else (self.price * coupon.discount_value / 100)
            ),
        )

        if best_coupon.discount_type == COUPON_CHOICE.PERCENTAGE:
            discount_value = (best_coupon.discount_value / 100) * self.price
        else:
            discount_value = min(best_coupon.discount_value, self.price)

        return {
            "code": best_coupon.code,
            "discount_value": discount_value,
            "discount_type": best_coupon.get_discount_type_display(),
        }

    def __str__(self):
        if not self.title:
            logger.error(f"Product ID {self.id} has no title")
            return f"Product ID {self.id}"
        return self.title


class ProductKey(TimeBasedModel):
    product = auto_prefetch.ForeignKey(
        "ecommerce.Product",
        verbose_name=_("Product Key"),
        on_delete=SET_NULL,
        null=True,
    )
    key = CharField(max_length=255)
    password = CharField(max_length=255)
    is_used = BooleanField(default=False)

    def __str__(self) -> str:
        return (
            f"key for {self.product.title} - key {self.key} - password{self.password}"  # noqa
        )


class ProductImages(ImageTitleTimeBaseModels):
    product = auto_prefetch.ForeignKey(
        Product,
        verbose_name=_("Product image"),
        on_delete=SET_NULL,
        null=True,
    )

    class Meta:
        verbose_name_plural = "Product images"


class CartOrder(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User",
        verbose_name=_("User Order"),
        on_delete=CASCADE,
        null=True,
        related_name="cart_orders",
    )
    price = DecimalField(
        max_digits=100,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    paid_status = BooleanField(default=False)
    product_status = CharField(
        choices=ProductStatus.choices,
        default=ProductStatus.PROCESSING,
        max_length=30,
    )
    payment_method = CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = "Cart Orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user}'s cart order"


class CartOrderItems(TimeBasedModel):
    transaction_id = CharField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        blank=True,
    )
    order = auto_prefetch.ForeignKey(
        CartOrder,
        verbose_name=_("Order"),
        on_delete=CASCADE,
        null=True,
        related_name="order_items",
    )
    product = auto_prefetch.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=SET_NULL,
        null=True,
    )
    unique_key = CharField(max_length=255, blank=True, null=True)
    quantity = IntegerField(default=1, validators=[MinValueValidator(1)])
    price = DecimalField(
        max_digits=100,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = DecimalField(
        max_digits=100,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    invoice_no = CharField(max_length=50, default="", blank=True)
    keys_and_passwords = JSONField(default=list, blank=True)

    class Meta:
        verbose_name_plural = "Cart Order Items"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        """
        Saves the object after checking and generating
        a transaction ID if not already set.
        Parameters:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)

    def unique_keys_list(self):
        return [entry["key"] for entry in self.keys_and_passwords]

    def __str__(self):
        return f"{self.product} - {self.quantity} item(s)"


class Payment(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=CASCADE,
        related_name="payments",
        default="",
        blank=True,
    )
    order = auto_prefetch.OneToOneField(
        "ecommerce.CartOrder",
        on_delete=CASCADE,
        related_name="payment",
        default="",
        blank=True,
        null=True,
    )
    wallet = auto_prefetch.ForeignKey(
        "refer.Wallet",
        on_delete=CASCADE,
        related_name="payments",
        blank=True,
        null=True,
    )
    amount = DecimalField(
        max_digits=100,
        decimal_places=2,
        default="",
        blank=True,
    )
    reference = CharField(
        max_length=100,
        unique=True,
        default="",
        blank=True,
    )
    payment_id = CharField(blank=True, null=True)
    status = CharField(
        max_length=20,
        default="pending",
        blank=True,
    )
    verified = BooleanField(default=False)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self) -> str:
        return f"Payment for {self.order}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            # Generate unique reference
            self.reference = self.generate_unique_reference()
        if not self.pk and not self.payment_id:
            self.payment_id = self.generate_payment_id()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_payment_id():
        latest_id = Payment.objects.latest("id").id if Payment.objects.exists() else 0  # noqa
        return latest_id + str(1)

    @staticmethod
    def generate_unique_reference():
        return str(uuid.uuid4())

    def amount_value(self) -> int:
        return int(self.amount * 100)

    def verify_paystack_payment(self) -> bool:
        # Paystack payment verification
        paystack = PayStack()
        status, result = paystack.verify_payment(self.reference)
        if status:
            paystack_amount = (
                Decimal(result["amount"]) / 100
            )  # Amount in kobo to NGN                # noqa
            self.amount = paystack_amount
            if paystack_amount == self.amount:
                self.status = "verified"
                self.save()
                self.order.paid_status = True
                self.order.save()
                return True
        self.status = "failed"
        self.save()
        return False

    def verify_flutterwave_payment(self) -> bool:
        """
        Verifies the payment with Flutterwave
        and updates the payment status.

        Returns:
            bool: True if the payment is successfully verified,
            False otherwise
        """
        flutterwave = Flutterwave()
        exchange_rate = get_exchange_rate()
        logging.info(
            f"Starting verification for payment reference: {self.reference}",
        )

        try:
            # Fetch expected amount and currency from self
            expected_amount = convert_to_naira(self.amount, exchange_rate)
            expected_currency = "NGN"

            # Perform the payment verification using the tx_ref
            result = flutterwave.verify_payment(
                self.reference,
                expected_amount,
                expected_currency,
            )
            logging.info(f"Flutterwave verification result: {result}")

            if result["status"] == "success":
                # Removed the amount comparison logic

                # Update payment status
                self.status = "verified"
                self.save()

                # Update the order's paid status
                self.order.paid_status = True
                self.order.save()

                logging.info(
                    f"Payment reference {self.reference} successfully verified."  # noqa
                )
                return True
            logging.error(
                f"Verification failed for payment reference {self.reference}: "  # noqa
                f"status {result['status']}, message {result.get('message')}."
            )

        except (KeyError, ValueError) as e:
            logging.exception(
                f"Error during verification for payment reference {self.reference}: {e}"  # noqa
            )

        except Exception as e:
            logging.exception(
                f"Unexpected error during verification for payment reference {self.reference}: {e}"  # noqa
            )

        return False

    def verify_payment_nowpayments(self, request) -> bool:
        """
        Verifies a payment made via NOWPayments.

        Args:
            request (HttpRequest): The request object.

        Returns:
            bool: True if the payment is successfully verified,
            False otherwise.
        """
        nowpayment = NowPayment()

        # Ensure payment_id is present
        if not self.payment_id:
            messages.error(request, "Payment ID is missing.")
            self.status = "failed"
            self.save()
            return False

        # Verify payment with NOWPayments API using payment_id as an integer
        success, result = nowpayment.verify_payment(int(self.payment_id))
        self.status = "observing"
        self.save()
        messages.info(request, f"NowPayments verification result: {result}")

        # Check if the API call was successful
        # and if payment status is available
        if not success or "payment_status" not in result:
            messages.error(
                request,
                "No response from NOWPayments API or payment status is not available.",  # noqa
            )
            self.status = "failed"
            self.save()
            return False

        # Confirm if payment status is 'confirmed'
        if result.get("payment_status") == "confirmed":
            # Convert pay_amount to a float or string
            nowpayments_amount = Decimal(result.get("pay_amount", 0))

            # Verify if the amount paid matches the expected amount
            if nowpayments_amount == self.amount:
                self.status = "verified"
                self.verified = True
                self.amount = nowpayments_amount
                self.save()

                # Mark the order as paid
                self.order.paid_status = True
                self.order.save()

                # Inform the user of successful verification
                messages.success(
                    request,
                    "Payment successfully confirmed and verified.",
                )
                return True
            messages.error(
                request,
                "Payment amount mismatch. Verification failed.",
            )

        # If payment verification fails
        messages.error(request, "Payment verification failed.")
        self.status = "failed"
        self.save()
        return False

    def verify_wallet_payment(self, request) -> bool:
        """
        Verifies the wallet payment and checks if the
        wallet has sufficient balance.
        Updates status, deducts balance, and saves changes as necessary.

        Returns:
            bool: True if the wallet payment is successfully verified,
            False otherwise.
        """
        if not self.wallet:
            messages.error(request, "No associated wallet found.")
            self.status = "failed"
            self.save()
            return False

        try:
            with transaction.atomic():
                # Debit the wallet using the wallet's debit method
                self.wallet.debit_wallet(self.amount)

                # Update payment status
                self._update_verification_status(
                    verified=True,
                    message="Wallet payment verified successfully.",
                    request=request,
                )
                return True

        except ValueError as e:
            # Catching insufficient balance or other ValueError exceptions
            messages.error(request, str(e))
            self.status = "failed"
            self.save()
            return False

    def _update_verification_status(
            self, verified: bool, message: str, request
    ):
        """
        Internal helper to update the status of the payment
        and display a message.
        """
        self.status = "verified" if verified else "failed"
        self.verified = verified
        self.save()
        if verified:
            messages.success(request, message)
        else:
            messages.error(request, message)

    @classmethod
    def generate_tx_ref(cls):
        """Generates a unique transaction reference."""
        return f"{uuid.uuid4().hex[:10]}"


class ProductReview(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User",
        verbose_name=_("User Review"),
        on_delete=SET_NULL,
        null=True,
    )
    product = auto_prefetch.ForeignKey(
        Product,
        verbose_name=_("Product Review"),
        on_delete=SET_NULL,
        null=True,
    )
    review = TextField()
    rating = IntegerField(choices=Rating.choices, default=Rating.THREE_STARS)

    class Meta:
        verbose_name_plural = "Product Reviews"

    def get_rating(self):
        return self.rating


class WishList(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User",
        verbose_name=_("User"),
        on_delete=SET_NULL,
        null=True,
    )
    product = auto_prefetch.ForeignKey(
        Product,
        verbose_name=_("Product Wishlist"),
        on_delete=SET_NULL,
        null=True,
    )

    class Meta:
        verbose_name_plural = "Wishlists"
        ordering = ["-created_at"]

    def get_rating(self):
        return f"products wishlist : {self.rating}"  # noqa


class Address(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User",
        verbose_name=_("User Address"),
        on_delete=SET_NULL,
        null=True,
    )
    address = CharField(max_length=100, default="", blank=True)
    status = BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Address"

    def get_rating(self):
        return f"products address : {self.address}"  # noqa


class Coupon(TimeBasedModel):
    code = CharField(
        max_length=20,
        unique=True,
        help_text="Unique coupon code.",
    )
    discount_type = CharField(
        max_length=10,
        choices=COUPON_CHOICE.choices,
        help_text="Type of discount.",
    )
    discount_value = DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Value of the discount. For percentage, use values between 0 and 100.",  # noqa
    )
    applicable_products = ManyToManyField(
        Product,
        blank=True,
        help_text="Products to which the coupon applies.",
    )
    applicable_categories = ManyToManyField(
        Category,
        blank=True,
        help_text="Categories to which the coupon applies.",
    )
    universal = BooleanField(
        default=False,
        help_text="If True, this coupon applies to all products and categories.",  # noqa
    )
    usage_limit = PositiveIntegerField(
        default=1,
        help_text="Maximum number of times the coupon can be used.",
    )
    times_used = PositiveIntegerField(
        default=0,
        editable=False,
        help_text="How many times the coupon has been used.",
    )
    valid_from = DateField(
        null=True,
        blank=True,
        help_text="Start date of coupon validity.",
    )
    valid_to = DateField(
        null=True,
        blank=True,
        help_text="End date of coupon validity.",
    )

    class Meta:
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                check=Q(valid_to__gte=F("valid_from")),
                name="valid_to_after_valid_from",
            ),
        ]

    def __str__(self):
        return (
            f"{self.code} ({self.get_discount_type_display()}: {self.discount_value})"  # noqa
        )

    def is_valid(self):
        """Check if the coupon is still valid."""
        today = timezone.now().date()
        return (
            self.times_used < self.usage_limit
            and (self.valid_from is None or self.valid_from <= today)
            and (self.valid_to is None or self.valid_to >= today)
        )
