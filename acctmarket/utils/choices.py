import pycountry
from django.db.models import IntegerChoices, TextChoices


class ProductStatus(TextChoices):
    PROCESSING = ("PROCESSING", "PROCESSING")
    SHIPPED = ("SHIPPED", "SHIPPED")
    DELIVERED = ("DELIVERED", "DELIVERED")


class Status(TextChoices):
    DRAFT = ("DRAFT", "DRAFT")
    DISABLED = ("DISABLED", "DISABLED")
    IN_REVIEW = ("IN_REVIEW", "IN_REVIEW")
    REJECTED = ("REJECTED", "REJECTED")
    PUBLISHED = ("PUBLISHED", "PUBLISHED")


class Rating(IntegerChoices):
    ONE_STAR = 1, "⭐"
    TWO_STARS = 2, "⭐⭐"
    THREE_STARS = 3, "⭐⭐⭐"
    FOUR_STARS = 4, "⭐⭐⭐⭐"
    FIVE_STARS = 5, "⭐⭐⭐⭐⭐"


class Ticket(TextChoices):
    OPEN = ("OPEN", "OPEN")
    IN_PROGRESS = ("IN_PROGRESS", "IN_PROGRESS")
    CLOSED = ("CLOSED", "CLOSED")


class WalletTransactionTypeChoice(TextChoices):
    CREDIT = ("CREDIT", "CREDIT")
    DEBIT = ("DEBIT", "DEBIT")


class NOTIFICATION_TYPES_Choice(TextChoices):
    WALLET_DEBIT = ("WALLET_DEBIT", "WALLET_DEBIT")
    WALLET_CREDIT = ("WALLET_CREDIT", "WALLET_CREDIT")
    PAYMENT_fAILED = ("PAYMENT_fAILED", "PAYMENT_fAILED")
    PAYMENT_SUCCESS = ("PAYMENT_SUCCESS", "PAYMENT_SUCCESS")


class TIER_CHOICE_TYPE(TextChoices):
    STARTER = ("Starter", "Starter")
    POWER_REFERRER = ("Power Referrer", "Power Referrer")
    ELITE_REFERRER = ("Elite Referrer'", "Elite Referrer")


class COUPON_CHOICE(TextChoices):
    PERCENTAGE = ("Percentage", "Percentage")
    FIXED = ("Fixed", "Fixed")


class SMSCampaignStatusChoices(TextChoices):
    SENT = ("Sent", "Sent")
    DRAFT = ("Draft", "Draft")
    FAILED = ("Failed", "Failed")
    SCHEDULED = ("Scheduled", "Scheduled")
    NO_RECIPIENTS = ("No recipient", "No recipient")


def get_region_choices():
    return [(country.alpha_2, country.name) for country in pycountry.countries]
