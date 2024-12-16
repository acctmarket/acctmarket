import logging
from decimal import Decimal

import auto_prefetch
from django.db import models, transaction

from acctmarket.applications.refer.manager import ReferralManager
from acctmarket.applications.users.models import Customer
from acctmarket.applications.users.services import TwilloSMSService
from acctmarket.utils.choices import (TIER_CHOICE_TYPE,
                                      NOTIFICATION_TYPES_Choice,
                                      SMSCampaignStatusChoices,
                                      WalletTransactionTypeChoice)
from acctmarket.utils.models import TimeBasedModel

# Create your models here.
logger = logging.getLogger(__name__)


class Referral(TimeBasedModel):
    """
    Represents a referral made by a user.

    - `referrer`: The user who referred someone.
    - `referred_user`: The user who was referred.
    - `referral_code`: The unique code used for referral.
    - `is_completed`: Whether the referral process was
    successfully completed (e.g., signup or purchase).
    """

    referrer = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="referrals_made",
    )
    referred_user = auto_prefetch.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refered_by",
    )
    referral_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
    )
    total_referred_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        null=True,
        blank=True,
    )
    first_purchase_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_completed = models.BooleanField(default=False)
    referred_user_signup_completed = models.BooleanField(
        default=False,
        blank=True,
        null=True,
    )
    wallet_funded = models.BooleanField(
        default=False,
        blank=True,
        null=True,
    )
    first_purchase_done = models.BooleanField(default=False)

    objects = ReferralManager()

    class Meta:
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Referral by {self.referrer.username}"

    @staticmethod
    def get_successful_referrals(referrer):
        """
        Retrieve a queryset of successfully referred users by a given referrer.

        Args:
            referrer (User): The user who made the referrals.

        Returns:
            QuerySet: A queryset of successful referrals
                    for the given referrer.
        """
        return Referral.objects.filter(
            referrer=referrer,
            # is_completed=True,  # Filter for completed referrals
            referred_user__isnull=False,  # Ensure there's a referred user
        ).select_related("referred_user")

    def apply_first_purchase_reward(self, purchase_amount):
        """
        Applies first purchase commission to the referrer.
        """
        if self.first_purchase_done:
            return  # Referral is already completed

        # referrer_customer = self.referrer.customer
        # Retrieve the Customer profile and wallet  associated with the referrer    # noqa
        try:
            referrer_customer = Customer.objects.get(
                user=self.referrer,
            )
            referrer_wallet = Wallet.objects.get(
                user=self.referrer,
            )
            logger.info(
                f"getting the referrers wallet for first purchase {referrer_wallet}"  # noqa
            )  # noqa
        except (Customer.DoesNotExist, Wallet.DoesNotExist):
            # Handle the case where no Customer profile exists for the referrer
            raise ValueError(
                f"No Customer profile or wallet found for user {self.referrer}"
            )  # noqa
        tier_commission_map = {
            TIER_CHOICE_TYPE.STARTER: Decimal("0.10"),
            TIER_CHOICE_TYPE.POWER_REFERRER: Decimal("0.12"),
            TIER_CHOICE_TYPE.ELITE_REFERRER: Decimal("0.15"),
        }
        tier_rate = tier_commission_map.get(
            referrer_customer.tier,
            Decimal("0.07"),
        )
        commission = min(purchase_amount * tier_rate, Decimal("70.00"))
        # Update balances
        referrer_customer.commission_balance += commission
        referrer_wallet.credit_wallet(commission)
        # Mark referral as completed
        self.first_purchase_done = True
        self.is_completed = True
        self.first_purchase_amount = purchase_amount
        self.save(
            update_fields=[
                "first_purchase_done",
                "is_completed",
                "first_purchase_amount",
            ]
        )

    def apply_ongoing_commission(self, purchase_amount):
        try:
            referrer_customer = Customer.objects.get(user=self.referrer)
            referrer_wallet = Wallet.objects.get(user=self.referrer)
        except (Customer.DoesNotExist, Wallet.DoesNotExist):
            raise ValueError(
                f"No Customer profile or Wallet found for user {self.referrer}"
            )  # noqa

        # Calculate ongoing commission
        tier_rate_map = {
            TIER_CHOICE_TYPE.STARTER: Decimal("0.01"),
            TIER_CHOICE_TYPE.POWER_REFERRER: Decimal("0.015"),
            TIER_CHOICE_TYPE.ELITE_REFERRER: Decimal("0.02"),
        }
        tier_rate = tier_rate_map.get(referrer_customer.tier, Decimal("0.01"))
        commission = purchase_amount * tier_rate
        # Update balances
        referrer_customer.commission_balance += commission
        referrer_wallet.credit_wallet(commission)

    def finalize_referral(self):
        """
        Completes the referral process and rewards the referred user.
        """
        if self.is_completed:
            return

        try:
            self.referred_user.wallet.credit_wallet(Decimal("0.50"))
        except AttributeError:
            raise ValueError("Referred user does not have a wallet.")

        self.is_completed = True
        self.save(update_fields=["is_completed"])

    def check_and_complete_referral(self):
        """
        Checks if all conditions are met to complete the referral.
        If so, applies the $0.5 bonus to the referred user's wallet.
        """
        print("signals got here ..........................")
        if self.wallet_funded and not self.is_completed:
            self.referred_user.wallet.credit_wallet(Decimal("0.50"))
            print(self.referred_user, "<<<<<<<<<<<<>>>>>>>>>>>>>>>")
            self.is_completed = True
            self.first_purchase_done = True
            self.save(update_fields=["is_completed", "first_purchase_done"])


class Wallet(TimeBasedModel):
    """
    Represents a user's wallet to store referral rewards.

    - `user`: The user who owns the wallet.
    - `balance`: The current balance of the wallet.
    """

    user = auto_prefetch.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    referral_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return f"Wallet of {self.user} (Balance: {self.balance})"

    @transaction.atomic
    def credit_wallet(self, amount):
        """Credits the wallet with a specified amount."""
        if amount <= 0:
            logger.error(
                "Attempted to credit wallet with non-positive amount.",
            )
            raise ValueError(
                "Amount must be positive to credit the wallet.",
            )

        logger.info(
            f"Crediting wallet of user {self.user.username} with amount {amount}."  # noqa
        )  # noqa

        # Perform balance update and save
        self.balance += Decimal(amount)
        self.save(update_fields=["balance"])

        # Record transaction history
        self.record_transaction(
            amount,
            WalletTransactionTypeChoice.CREDIT,
        )
        # Create a notification
        Notification.objects.create(
            user=self.user,
            message=f"Your wallet has been credited with {amount}.",
            notification_type=NOTIFICATION_TYPES_Choice.WALLET_CREDIT,
        )

    @transaction.atomic
    def debit_wallet(self, amount):
        """Debits the wallet with a specified amount."""
        if amount > self.balance:
            raise ValueError("Insufficient balance.")
        self.balance -= amount
        self.save()
        self.record_transaction(amount, "debit")
        # Create a notification
        Notification.objects.create(
            user=self.user,
            message=f"Your wallet has been debited by {amount}.",
            notification_type="wallet_debit",
        )

    def apply_admin_fee(self, amount):
        """Apply a 10% admin fee to the wallet transaction."""
        admin_fee = amount * Decimal("0.10")
        self.debit_wallet(admin_fee)

    def record_transaction(self, amount, transaction_type):
        """Records a transaction history for tracking purposes."""
        logger.info(
            f"Recording {transaction_type} transaction for user {self.user.name} with amount {amount}."  # noqa
        )  # noqa
        WalletTransaction.record_transaction(
            self,
            amount,
            transaction_type,
        )

    def spend_referral_balance(self, amount):
        """
        Allow users to spend their referral balance
        within the platform only.
        """
        if amount > self.referral_balance:
            raise ValueError("Insufficient referral balance.")
        self.referral_balance -= amount
        self.save(update_fields=["referral_balance"])


class WalletTransaction(TimeBasedModel):
    """
    Tracks individual wallet transactions (credits and debits).

    - `wallet`: Reference to the wallet.
    - `amount`: The transaction amount.
    - `transaction_type`: Type of transaction, either 'credit' or 'debit'.

    """

    wallet = auto_prefetch.ForeignKey(
        "refer.Wallet",
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(
        max_length=6,
        choices=WalletTransactionTypeChoice.choices,
        default=WalletTransactionTypeChoice.DEBIT,
    )

    class Meta:
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"
        ordering = ["-created_at"]

    @classmethod
    def record_transaction(cls, wallet, amount, transaction_type):
        """Creates a new wallet transaction record."""
        logger.info(
            f"Recording transaction: {transaction_type} of {amount} for wallet {wallet.id}"  # noqa
        )

        # Create and save the transaction
        transaction = cls(
            wallet=wallet,
            amount=amount,
            transaction_type=transaction_type,
        )
        transaction.save()

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of {self.amount:.2f} on {self.wallet.user.username}'s wallet"  # noqa


class Notification(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES_Choice.choices,
    )
    read = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} - {self.user.username}"

    def mark_as_read(self):
        """Marks the notification as read."""
        self.read = True
        self.save()

    @classmethod
    def get_unread_count(cls, user):
        """Returns the count of unread notifications for a user."""
        return cls.objects.filter(user=user, read=False).count()


class SMSCampaign(TimeBasedModel):
    name = models.CharField(
        max_length=255,
        help_text="The name of the SMS campaign for identification.",
    )
    message = models.TextField(
        help_text="The SMS message content to be sent to recipients.",
    )
    status = models.CharField(
        max_length=20,
        choices=SMSCampaignStatusChoices.choices,
        default=SMSCampaignStatusChoices.DRAFT,
        help_text="The current status of the SMS campaign.(leave as draft system will update authomatically)",  # noqa
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time to send the campaign.",
    )

    class Meta:
        verbose_name = "SMS Campaign"
        verbose_name_plural = "SMS Campaigns"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name

    def get_opted_in_customers(self):
        """
        Retrieves all customers who have opted in for SMS notifications
        and have valid phone numbers.
        """
        return Customer.objects.filter(
            sms_opt_in=True,
            user__phone_no__isnull=False,
        ).exclude(user__phone_no__exact="")

    def get_opted_in_customers_count(self):
        """
        Returns the count of opted-in customers with valid phone numbers.
        """
        return self.get_opted_in_customers().count()

    def send_to_users(self):
        """
        Sends the SMS campaign to all opted-in customers.
        Updates the campaign's status and sent_at timestamp.
        """
        if self.status != SMSCampaignStatusChoices.DRAFT:
            logger.warning(
                f"Campaign '{self.name}' cannot be sent as it is not in 'draft' status.",  # noqa
            )
            return False

        # Fetch all opted-in customers
        opted_in_customers = self.get_opted_in_customers()
        if not opted_in_customers.exists():
            logger.warning(
                f"No opted-in customers found for campaign '{self.name}'.",
            )
            self.status = SMSCampaignStatusChoices.NO_RECIPIENTS
            self.save()
            return False

        # Initialize SMS service
        sms_service = TwilloSMSService()

        # Send SMS to each customer and collect results
        results = []
        for customer in opted_in_customers:
            # Get the formatted phone number from the User instance
            phone_no = customer.user.formatted_phone_number
            if phone_no:
                result = sms_service.send_sms(phone_no, self.message)
                results.append(result)
                if result:
                    logger.info(f"SMS sent to {phone_no}: {result}")
            else:
                logger.warning(
                    f"Invalid phone number for user {customer.user.email}",
                )

        # Update the campaign's status and sent_at timestamp
        if results:
            self.status = SMSCampaignStatusChoices.SENT
            self.save()
            logger.info(
                f"Campaign '{self.name}' successfully sent to {len(results)} recipients.",  # noqa
            )
            return True
        logger.error(f"Campaign '{self.name}' failed to send any messages.")
        self.status = SMSCampaignStatusChoices.FAILED
        self.save()
        return False

    def is_sent(self):
        """
        Checks if the campaign is marked as sent.
        """
        return self.status == SMSCampaignStatusChoices.SENT
