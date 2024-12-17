from django.urls import path

from acctmarket.applications.refer.views import (FlutterWalletFundView,
                                                 FlutterwaveCallbackView,
                                                 MarkAllNotificationsReadView,
                                                 NotificationListView,
                                                 NowPaymentCallbackView,
                                                 NowPaymentWalletFundView,
                                                 ReferralListView,
                                                 SMSCampaignCreateView,
                                                 SMSCampaignDetailView,
                                                 SMSCampaignListView,
                                                 SMSCampaignSendView,
                                                 SMSCampaignUpdateView,
                                                 WalletDetailView,
                                                 WalletFundingCancelView,
                                                 WalletFundingSuccessView,
                                                 WalletTrasactionListViews)

app_name = "referals"
urlpatterns = [
    path("", ReferralListView.as_view(), name="referals_list"),
    path(
        "my-wallet",
        WalletDetailView.as_view(), name="walet_detail"
    ),
    path(
        "fund-wallet/now-payment",
        NowPaymentWalletFundView.as_view(), name="fund_wallet"
    ),
    path(
        "fund-wallets/flutter-wave",
        FlutterWalletFundView.as_view(), name="fund_wallet2"
    ),
    path(
        "wallet/funding-callback/",
        FlutterwaveCallbackView.as_view(), name="flutterwave_callback"
    ),
    path(
        "wallet/nowpayment-callback",
        NowPaymentCallbackView.as_view(),
        name="nowpayment_callback"
    ),
    path(
        "funding-success/",
        WalletFundingSuccessView.as_view(), name="funding_success"
    ),
    path(
        "funding-cancel/",
        WalletFundingCancelView.as_view(), name="funding_cancel"
    ),
    path(
        "transactions/", WalletTrasactionListViews.as_view(),
        name="wallet_transaction_list"
    ),
    path(
        "notifications/", NotificationListView.as_view(),
        name="notifications"
    ),
    path(
        "notifications/mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="mark_all_notifications_read"
    ),
    path(
        "campaigns/", SMSCampaignListView.as_view(),
        name="sms_campaign_list"
    ),
    path(
        "campaigns/<int:pk>/", SMSCampaignDetailView.as_view(),
        name="sms_campaign_detail"
    ),
    path(
        "campaigns/create/", SMSCampaignCreateView.as_view(),
        name="sms_campaign_create"
    ),
    path(
        "campaigns/<int:pk>/update/", SMSCampaignUpdateView.as_view(),
        name="sms_campaign_update"
    ),
    path(
        "campaigns/<int:pk>/send/", SMSCampaignSendView.as_view(),
        name="sms_campaign_send"
    ),
]
