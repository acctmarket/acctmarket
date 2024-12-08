
import logging
import threading
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from acctmarket.applications.ecommerce.models import CartOrder
from acctmarket.applications.refer.models import Referral, SMSCampaign, Wallet
from acctmarket.applications.users.models import Customer, User
from acctmarket.utils.choices import SMSCampaignStatusChoices

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_related_objects(sender, instance, created, **kwargs):
    """
    Signal to handle the creation of user-related objects
    (wallet).

    - Creates a wallet for the user upon signup.
    """
    if not created:
        return  # Only process on user creation

    # Start a transaction block to ensure atomicity
    with transaction.atomic():
        Wallet.objects.get_or_create(user=instance)


@receiver(post_save, sender=Wallet)
def handle_wallet_post_save(sender, instance, created, **kwargs):
    """
    Handles referral bonus when the
    wallet is funded sufficiently.
    """
    if created:
        return  # Only handle updates

    wallet = instance
    user = wallet.user

    try:
        referral = Referral.objects.select_related("referred_user").get(
            referred_user=user
        )
        logger.debug(
            f"Referral found for user {user} with referral ID {referral.id}."
        )
    except Referral.DoesNotExist:
        logger.info(f"No referral associated with user {user}. Skipping.")
        return  # No referral associated

    with transaction.atomic():
        if not referral.wallet_funded and wallet.balance >= Decimal("5.00"):
            logger.info(
                f"Wallet for user {user} funded with sufficient balance. "
                f"Updating referral ID {referral.id}."
            )
            referral.wallet_funded = True
            referral.save(update_fields=["wallet_funded"])
            logger.debug(
                f"Referral ID {referral.id} marked as wallet funded. "
                f"Initiating referral completion."
            )
            try:
                referral.check_and_complete_referral()
                logger.info(
                    f"Referral completion logic executed for referral ID {referral.id}."  # noqa
                )
            except Exception as e:
                logger.error(
                    f"Error completing referral logic for referral ID {referral.id}: {e}",  # noqa
                    exc_info=True,
                )


@receiver(post_save, sender=CartOrder)
def handle_order_post_save(sender, instance: CartOrder, created, **kwargs):
    """
    Handles referral rewards after an order is created or marked as paid.
    Updates the total spend for referred users.
    """
    logger.info(f"Post-save signal triggered for Payment ID: {instance.id}")

    # Exit if payment is not marked as paid
    if not instance.paid_status:
        logger.info("Payment not marked as paid. Exiting signal.")
        return

    referred_user = instance.user
    logger.info(f"Processing referral for user: {referred_user}")

    try:
        referral = Referral.objects.select_related("referrer").get(
            referred_user=referred_user
        )
    except Referral.DoesNotExist:
        logger.info("No referral found for this user. Exiting signal.")
        return

    # Start a transaction to handle the updates atomically
    with transaction.atomic():
        # Handle first purchase reward
        if not referral.first_purchase_done and instance.price >= Decimal("5.00"):  # noqa
            try:
                logger.info("Applying first purchase reward.")
                referral.apply_first_purchase_reward(instance.price)
                referral.first_purchase_done = True
                referral.save(update_fields=["first_purchase_done"])
            except ValueError as e:
                logger.error(f"First purchase reward error: {str(e)}")

        # Handle ongoing commissions for subsequent purchases
        elif referral.first_purchase_done:
            try:
                logger.info("Applying ongoing commission.")
                referral.apply_ongoing_commission(instance.price)
            except ValueError as e:
                logger.error(f"Ongoing commission error: {str(e)}")

        # Update the total referred spend
        # (this is what tracks referred user spending)
        logger.info(
            f"Updating referred user's total spend for referral ID: {referral.id}"  # noqa
        )
        referral.total_referred_spend += instance.price  # Update total spend
        referral.save(update_fields=["total_referred_spend"])

        # Optional: Update user tier based on new total spend
        logger.info("Updating referrer's tier based on new total spend.")
        try:
            # Fetch the Customer profile associated with the referrer
            referrer_customer = Customer.objects.get(user=referral.referrer)
            referrer_customer.update_tier()
        except Customer.DoesNotExist:
            logger.error(f"No Customer profile found for referrer: {referral.referrer}. Cannot update tier.")  # noqa


@receiver(post_save, sender=SMSCampaign)
def send_sms_campaign(sender, instance, created, **kwargs):
    """
    This signal is triggered when an SMSCampaign is created or updated.
    It will attempt to send the SMS if the campaign is in 'draft' status.
    """
    print("we are here now .>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    if created or instance.status == SMSCampaignStatusChoices.DRAFT:
        # If it's a draft campaign, trigger sending SMS in a separate thread
        logger.info(f"Campaign '{instance.name}' created or updated, attempting to send SMS.")  # noqa

        # Start a new thread to handle sending the campaign
        threading.Thread(
            target=send_sms_campaign_task, args=(instance.id,)
        ).start()


def send_sms_campaign_task(campaign_id):
    """
    Sends the SMS campaign to all opted-in users in a background thread.
    """

    try:
        campaign = SMSCampaign.objects.get(id=campaign_id)

        # Ensure campaign is in 'draft' status
        if campaign.status != SMSCampaignStatusChoices.DRAFT:
            logger.warning(
                f"Campaign '{campaign.name}' is not in draft status. Skipping."
            )
            return
        # Call the send_to_users method to send the SMS
        result = campaign.send_to_users()

        # Log the result and update the campaign status
        if result:
            logger.info(f"Campaign '{campaign.name}' successfully sent.")
        else:
            logger.error(f"Campaign '{campaign.name}' failed to send.")
    except SMSCampaign.DoesNotExist:
        logger.error(f"Campaign with ID {campaign_id} does not exist.")
    except Exception as e:
        logger.error(f"Error while sending SMS campaign '{campaign_id}': {e}")
