# Register your models here.
import logging

from django.contrib import admin

from acctmarket.applications.refer.models import (Notification, Referral,
                                                  SMSCampaign, Wallet,
                                                  WalletTransaction)
from acctmarket.utils.choices import SMSCampaignStatusChoices

# from django.utils.translation import gettext_lazy as _


# Register your models here.
logger = logging.getLogger(__name__)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "balance")


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "id", "referred_user",
        "referrer",
        "is_completed"
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "wallet", "amount", "transaction_type"


    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user", "read", "notification_type"

    )


@admin.register(SMSCampaign)
class SMSCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at")
    list_filter = ("status", "scheduled_at", "created_at")
    search_fields = ("name", "message")
    ordering = ("-created_at",)
    actions = ["send_campaign"]
    actions = ["send_campaign"]

    @admin.action(description='Send selected SMS campaigns')
    def send_campaign(self, request, queryset):
        """
        Custom action to trigger sending campaigns from the admin interface.
        """
        sent_count = 0
        for campaign in queryset.filter(status=SMSCampaignStatusChoices.DRAFT):
            if campaign.send_to_users():
                sent_count += 1

        self.message_user(
            request,
            f"{sent_count} campaign(s) sent successfully.",
            level="success" if sent_count > 0 else "warning"
        )
