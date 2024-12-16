import logging
import random
import secrets
from decimal import Decimal

import auto_prefetch
import phonenumbers
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.db.models import CharField, EmailField
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumbers import NumberParseException

from acctmarket.utils.choices import TIER_CHOICE_TYPE, get_region_choices
from acctmarket.utils.models import UIDTimeBasedModel

from .managers import UserManager

logger = logging.getLogger(__name__)


class User(UIDTimeBasedModel, AbstractUser):
    """
    Default custom user model for Acctmarket.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name: str = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email: str = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]
    phone_no: str = CharField(_("Phone number"), default=00, unique=True)
    phone_region = models.CharField(
        max_length=2,
        choices=get_region_choices(),
        default="NG",
        null=True,  # Allow NULL in the database
        blank=True,  # Allow blank in forms
        help_text="User's phone region code (e.g., 'NG' for Nigeria)",
    )
    country: str = CountryField(_("Country"), null=True, blank=True)
    phone_verified: bool = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        """
        Validate phone number uniqueness
        and format before saving.
        """
        if not self.is_phone_no_unique():
            raise ValidationError(
                f"The phone number {self.phone_no} is already in use."  # noqa
            )
        super().save(*args, **kwargs)

    def is_phone_no_unique(self):
        """Check if the phone number is unique for this user."""
        # Exclude the current instance when updating
        return (
            not User.objects.exclude(id=self.id)
            .filter(
                phone_no=self.phone_no,
            )
            .exists()
        )

    @classmethod
    def create_with_unique_phone(cls, phone_no, **kwargs):
        """Create a user ensuring phone_no is unique."""
        if cls.objects.filter(phone_no=phone_no).exists():
            raise ValidationError(
                f"The phone number {phone_no} is already in use.",
            )
        return cls.objects.create(phone_no=phone_no, **kwargs)

    def get_absolute_url(self) -> str:
        """Get URL for user's Details.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    def __str__(self) -> str:
        return self.email

    @property
    def formatted_phone_number(self):
        """
        Returns the user's phone number in E.164 format, or None if invalid.

        Returns:
            str: Phone number in E.164 format if valid, otherwise None.
        """
        try:
            # Use self.phone_region to provide context
            # if the country code is missing
            parsed_number = phonenumbers.parse(
                self.phone_no,
                self.phone_region,
            )
            # Check if the number is valid
            if phonenumbers.is_valid_number(parsed_number):
                # Return in E.164 format
                return phonenumbers.format_number(
                    parsed_number,
                    phonenumbers.PhoneNumberFormat.E164,
                )
            return None
        except NumberParseException:
            return None

    @property
    def role(self):
        """
        Return the user's role based on their associated profile.
        """
        if self.is_superuser:
            return "admin"
        if CustomerSupportRepresentative.objects.filter(user=self).exists():
            return "customer_support"
        if ContentManager.objects.filter(user=self).exists():
            return "content_manager"
        if Customer.objects.filter(user=self).exists():
            return "customer"
        return "unknown"

    def generate_otp(self):
        """
        Generates a 6-digit OTP and sets its expiration
        time (e.g., 10 minutes).
        """
        otp = f"{random.randint(100000, 999999)}"
        self.otp_code = otp
        self.otp_expiry = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
        return otp

    def verify_otp(self, otp_code):
        """
        Verifies if the provided OTP matches and is within the valid timeframe.
        """
        if self.otp_code == otp_code and timezone.now() <= self.otp_expiry:
            self.phone_verified = True
            # self.otp_code = None
            # self.otp_expiry = None
            self.save(update_fields=["phone_verified"])
            return True
        return False


class Account(UIDTimeBasedModel):
    owner = auto_prefetch.ForeignKey(
        User,
        related_name="owned_accounts",
        on_delete=models.CASCADE,
        verbose_name=_("Account Owner"),
    )
    status = models.CharField(
        _("Account Status"),
        max_length=20,
        default="active",
        null=True,
    )

    class Meta(UIDTimeBasedModel.Meta):
        verbose_name_plural = "Accounts"

    def __str__(self):
        return f"{self.status}"


class BaseProfile(UIDTimeBasedModel):
    """
    Base class for different types of profiles associated with users.
    """

    user = auto_prefetch.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(class)s_profiles",
        verbose_name=_("User"),
    )
    account = auto_prefetch.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        verbose_name=_("Account"),
        related_name="%(class)s_profiles",
    )

    class Meta(UIDTimeBasedModel.Meta):
        abstract = True
        # Ensures no duplicate profiles for the same user and account
        unique_together = ("user", "account")

    def save(self, *args, **kwargs):
        """
        Ensure a user has only one profile per account.
        """
        # Skip validation if the instance is not fully initialized
        if (
            not self.pk
            and self.__class__.objects.filter(
                user=self.user,
                account=self.account,
            ).exists()
        ):
            raise ValidationError(
                "This user already has a profile with this account.",
            )
        super().save(*args, **kwargs)


class Customer(BaseProfile):
    """
    Represents a customer
    and includes referral functionality.
    """

    referral_code = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        null=True,
    )
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )
    commission_balance = models.DecimalField(
        default=0,
        max_digits=10,
        decimal_places=2,
    )
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICE_TYPE.choices,
    )
    first_purchase = models.BooleanField(default=True)
    sms_opt_in = models.BooleanField(
        default=False,
        verbose_name="Opt-in for SMS promotions",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.user.name

    @staticmethod
    def generate_referral_code():
        """Generate a unique referral code."""
        for _ in range(5):  # Attempt up to 5 times  # noqa
            code = secrets.token_urlsafe(8)
            if not Customer.objects.filter(referral_code=code).exists():
                return code
        raise ValueError(
            "Unable to generate a unique referral code after multiple attempts."  # noqa
        )  # noqa

    def save(self, *args, **kwargs):
        """Ensure a unique referral code is set for the customer."""
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    @property
    def get_referral_link(self):
        """
        Generate a referral link that includes the user's referral code.

        Returns:
            str: A formatted message containing the referral
            link for the user to share.
        """
        if not self.referral_code:
            return "Referral code is not available."

        base_url = settings.SITE_URL
        referral_link = (
            f"{base_url}/users/signup/customer?referral_code={self.referral_code}"  # noqa
        )
        return f"Use this link to join and enjoy exclusive benefits!: {referral_link} "  # noqa

    def update_tier(self):
        """
        Updates the customer's referral tier
        based on referred users' spending.
        """
        total_spent = self.get_total_spent_by_referrals()
        if total_spent == Decimal("0.00"):
            # Optional: Log or notify if no spend has occurred yet.
            self.tier = TIER_CHOICE_TYPE.STARTER
        elif total_spent >= 1000:
            self.tier = TIER_CHOICE_TYPE.ELITE_REFERRER
        elif total_spent >= 500:
            self.tier = TIER_CHOICE_TYPE.POWER_REFERRER
        else:
            self.tier = TIER_CHOICE_TYPE.STARTER

        # Log the tier update for debugging purposes
        logger.info(
            f"User {self.user} tier updated to {self.tier} based on total spend of {total_spent}."  # noqa
        )  # noqa

        self.save()

    def get_total_spent_by_referrals(self):
        """
        Calculates the total amount spent by referred users.
        """
        from acctmarket.applications.refer.models import Referral

        # Ensure that the user exists (edge case handling)
        if not self.user:
            logger.warning(
                "No user associated with the referral. Exiting total spend calculation."  # noqa
            )  # noqa
            return Decimal("0.00")

        # Fetch the total spend of referred users by
        # summing 'total_referred_spend'
        total_spent = Referral.objects.filter(referrer=self.user).aggregate(
            total_spent=models.Sum("total_referred_spend"),
        )["total_spent"] or Decimal("0.00")

        # Enhanced logging for better insight
        if total_spent == Decimal("0.00"):
            logger.info(
                f"No spend recorded for referrals of user {self.user.username}."  # noqa
            )  # noqa

        return total_spent

    def update_referrer_commission(self, purchase_amount):
        """
        Updates the referrer's commission balance
        when a referred user makes a purchase.
        """
        commission = (
            purchase_amount * 0.07 if self.first_purchase else purchase_amount * 0.01  # noqa
        )  # noqa
        commission -= commission * 0.10  # Deduct admin fee (10%)

        self.commission_balance += commission
        self.first_purchase = False  # Mark as no longer first purchase
        self.save()

    def notify_referrer(self):
        """
        Notifies the referrer when the referral completes an action,
        such as a purchase.
        """
        if self.referred_by:
            referrer_email = self.referred_by.user.email
            send_mail(
                "Referral Successful",
                "Your referral has successfully signed up and made a purchase!",  # noqa
                "noreply@acctmarket.com",
                [referrer_email],
            )


class Administrator(BaseProfile):
    """
    Represents an administrator associated with an account.
    """

    department = models.CharField(_("Department"), max_length=100)

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Administrators"


class CustomerSupportRepresentative(BaseProfile):
    """
    Represents a customer support representative associated with an account.
    """

    department = models.CharField(_("Department"), max_length=100)

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Customer Support Representatives"

    def save(self, *args, **kwargs):
        if not self.department:
            self.department = (
                "General"  # Set default value if department is not provided
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.name


class ContentManager(BaseProfile):
    """
    Represents a content manager associated with an account.
    """

    expertise_area = models.CharField(_("Expertise Area"), max_length=255)

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Content Managers"

    def save(self, *args, **kwargs):
        if not self.expertise_area:
            self.expertise_area = "General"
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)


class MarketingAndSales(BaseProfile):
    """
    Represents a marketing and sales personnel associated with an account.
    """

    marketing_strategy = models.TextField(_("Marketing Strategy"))

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Marketing and Sales"

    def save(self, *args, **kwargs):
        if not self.marketing_strategy:
            self.marketing_strategy = "Perfect"  # Set default value if expertise_area is not provided                   # noqa
        super().save(*args, **kwargs)


class Accountant(BaseProfile):
    """
    Represents an accountant associated with an account.
    """

    financial_software_used = models.CharField(
        _("Financial Software Used"),
        max_length=100,
    )

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Accountants"

    def save(self, *args, **kwargs):
        if not self.financial_software_used:
            self.financial_software_used = "Real One"
        super().save(*args, **kwargs)


class HelpDeskTechnicalSupport(BaseProfile):
    """
    Represents a technical support personnel associated with an account.
    """

    technical_skills = models.TextField(_("Technical Skills"))

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Help Desk Technical Supports"

    def save(self, *args, **kwargs):
        if not self.technical_skills:
            self.technical_skills = "Web dev"
        super().save(*args, **kwargs)


class LiveChatSupport(BaseProfile):
    """
    Represents a live chat support personnel associated with an account.
    """

    languages_spoken = models.CharField(_("Languages Spoken"), max_length=100)

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Live Chat Supports"

    def save(self, *args, **kwargs):
        if not self.languages_spoken:
            self.languages_spoken = "English"
        super().save(*args, **kwargs)


class AffiliatePartner(BaseProfile):
    """
    Represents an affiliate partner associated with an account.
    """

    affiliate_code = models.CharField(_("Affiliate Code"), max_length=20)

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Affiliate Partners"

    def save(self, *args, **kwargs):
        if not self.affiliate_code:
            self.affiliate_code = "412"
        super().save(*args, **kwargs)


class DigitalGoodsDistribution(BaseProfile):
    """
    Represents digital goods distribution associated with an account.
    """

    delivery_method = models.CharField(_("Delivery Method"), max_length=50)

    class Meta(BaseProfile.Meta):
        verbose_name_plural = "Digital Goods Distributions"

    def save(self, *args, **kwargs):
        if not self.delivery_method:
            self.delivery_method = "Fast"
        super().save(*args, **kwargs)
