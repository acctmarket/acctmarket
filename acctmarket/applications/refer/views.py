# Create your views here.
# from django.shortcuts import render
import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (CreateView, DetailView, ListView,
                                  TemplateView, UpdateView, View)
from django.views.generic.edit import FormMixin

from acctmarket.applications.ecommerce.models import Payment
from acctmarket.applications.refer.forms import WalletFundingForm
from acctmarket.applications.refer.models import (Notification, Referral,
                                                  SMSCampaign, Wallet,
                                                  WalletTransaction)
from acctmarket.utils.choices import SMSCampaignStatusChoices
from acctmarket.utils.payments import (Flutterwave, NowPayment,
                                       convert_to_naira, get_exchange_rate)

# Create your views here.
logger = logging.getLogger(__name__)


class ReferralListView(LoginRequiredMixin, ListView):
    """
    Displays a list of successful referrals made by the logged-in user.
    Uses `LoginRequiredMixin` to ensure only logged-in users can access it.
    Filters the `Referral` model using `get_successful_referrals`
    for completed referrals by the current user.
    """
    model = Referral
    template_name = "pages/refer/referral_list.html"
    context_object_name = "referred_users"

    def get_queryset(self):
        """
        Use `get_successful_referrals` to retrieve the user's
        successful referrals.
        You can filter by successful referrals
        by adding the appropriate criteria.
        """
        return Referral.get_successful_referrals(self.request.user).filter(
            # is_completed=True,  # Filter for completed referrals
            referred_user__isnull=False  # Ensure there's a referred user
        )


class WalletDetailView(LoginRequiredMixin, TemplateView):
    """
    Displays the wallet details (balance) for the logged-in user.

    - Fetches the wallet instance based on the logged-in user.
    """
    template_name = "pages/refer/wallet_detail.html"

    def get_context_data(self, **kwargs):
        """
        Adds wallet data to the context for display in the template.
        """
        context = super().get_context_data(**kwargs)
        # Retrieve wallet or 404 if not found,
        # ensuring only the user's own wallet is accessed
        context["user_transactions"] = WalletTransaction.objects.filter(
            wallet__user=self.request.user
        ).order_by("-created_at")[:3]
        context["wallet"] = get_object_or_404(
            Wallet, user=self.request.user
        )
        return context


class WalletTrasactionListViews(LoginRequiredMixin, ListView):
    model = WalletTransaction
    template_name = "pages/refer/wallet_transaction_list.html"
    context_object_name = "transaction_lists"

    def get_queryset(self):
        # Get the user's wallet
        user_wallet = self.request.user.wallet
        return WalletTransaction.objects.filter(
            wallet=user_wallet
        ).order_by("-created_at")


class NowPaymentWalletFundView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        """
        Renders the wallet funding form to specify the amount.
        """
        form = WalletFundingForm()
        return render(
            request,
            "pages/refer/nowpaymentfund_wallet.html", {"form": form}
        )

    def post(self, request, *args, **kwargs):
        """
        Handles form submission to initiate funding via NOWPayments.
        """
        form = WalletFundingForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            nowpayment = NowPayment(
                callback_url_name="referals:nowpayment_callback",
                success_url_name="referals:funding_success",
                cancel_url_name="referals:funding_cancel"
            )

            # Create a new Payment instance for this transaction
            payment = Payment.objects.create(
                user=request.user,
                wallet=request.user.wallet,
                amount=amount,
                status="pending",
                order=None
            )

            # Create payment request to NOWPayments
            response = nowpayment.create_payment(
                amount=amount,
                currency="USD",
                order_id=payment.id,
                description="Wallet Funding",
                request=request
            )
            if response["status"]:
                payment.payment_id = response["data"]["id"]
                payment.save()
                logger.info(
                    f"Payment initialized successfully for user {request.user.id} with payment ID {payment.payment_id}."  # noqa
                )
                return redirect(response["data"]["invoice_url"])  #taking the user to the NOWPayments payment page.  # noqa
            else:
                messages.error(request, response["message"])
                logger.error(f"Failed to initialize payment for user {request.user.id}: {response['message']}")  # noqa
        return render(request, "wallet/fund_wallet.html", {"form": form})  # noqa


@method_decorator(csrf_exempt, name='dispatch')
class NowPaymentCallbackView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        logger.info("Received callback POST request.")

        # Step 1: Log the raw request body
        try:
            raw_body = request.body
            logger.debug(f"Raw request body (bytes): {raw_body}")

            # Decode it if it's in UTF-8, log it in case decoding fails
            decoded_body = raw_body.decode('utf-8')
            logger.debug(f"Decoded request body (string): {decoded_body}")
        except Exception as e:
            logger.error(f"Failed to decode request body: {str(e)}")
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Unable to process request body"
                },
                status=400
            )

        # Step 2: Parse JSON and log the parsed data
        try:
            data = json.loads(decoded_body)
            logger.debug(f"Parsed callback data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data in callback: {e}")
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON format"},
                status=400
            )

        # Step 3: Check for `payment_id` in data and log if missing
        payment_id = data.get("payment_id")
        if not payment_id:
            logger.error("No payment_id provided in callback data.")
            return JsonResponse(
                {"status": "error", "message": "Missing payment_id"},
                status=400
            )

        logger.info(f"Processing callback for payment ID: {payment_id}")

        # Retrieve the Payment instance
        payment = get_object_or_404(Payment, payment_id=payment_id)

        # Verify the payment status with NOWPayments
        nowpayment = NowPayment()
        status, response = nowpayment.verify_payment(payment_id)

        if status and response.get("payment_status") == "finished":
            try:
                with transaction.atomic():
                    # Update payment status and timestamp
                    payment.status = "completed"
                    payment.completed_at = timezone.now()
                    payment.save(update_fields=["status", "completed_at"])

                    # Credit the user's wallet
                    wallet = payment.wallet
                    wallet.credit_wallet(payment.amount)

                    # Log success
                    logger.info(
                        f"Payment ID {payment_id} verified and wallet credited with {payment.amount} for user {payment.user.username}."  # noqa
                    )
                    return JsonResponse({"status": "success", "message": "Wallet credited successfully"}, status=200)  # noqa

            except Exception as e:
                # Handle and log any errors during transaction processing
                logger.error(f"Error during transaction processing for payment ID {payment_id}: {str(e)}")  # noqa
                return JsonResponse({"status": "error", "message": "Transaction processing error"}, status=500)  # noqa
        else:
            # Handle invalid or incomplete payments
            logger.warning(f"Payment ID {payment_id} verification failed or incomplete.")  # noqa
            return JsonResponse({"status": "error", "message": "Invalid or incomplete payment status"}, status=400)  # noqa


# class FlutterWalletFundView(View):
#     """
#     Initiates wallet funding by creating a payment request to Flutterwave.
#     """
#     template_name = "pages/refer/flutterfund_wallet.html"

#     def get(self, request, *args, **kwargs):
#         """Render the wallet funding form for user input."""
#         return render(request, self.template_name)

#     def post(self, request, *args, **kwargs):
#         """Handles the form submission for initiating a wallet funding transaction."""  # noqa
#         amount = request.POST.get("amount")
#         currency = "USD"

#         if not amount or not amount.isdigit():
#             messages.error(request, "Amount is required.")
#             return render(request, self.template_name)

#         # Generate a unique transaction reference
#         flutterwave = Flutterwave()
#         tx_ref = f"{request.user.id}-{Payment.generate_tx_ref()}"

#         # Define success URL for payment completion
#         redirect_url = request.build_absolute_uri(
#             reverse_lazy("referals:funding_success")
#         )

#         customer_info = {
#             "email": request.user.email,
#             "phonenumber": request.user.phone_no,
#             "name": request.user.name,
#         }

#         # Initiate payment with Flutterwave
#         response = flutterwave.initiate_payment(
#             amount=amount,
#             currency=currency,
#             tx_ref=tx_ref,
#             redirect_url=redirect_url,  # Required redirect URL
#             customer=customer_info
#         )

#         # Check response status
#         if response.get("status") == "success":
#             # Record the payment in the system
#             Payment.objects.create(
#                 user=request.user,
#                 amount=amount,
#                 currency=currency,
#                 tx_ref=tx_ref,
#                 status="pending"
#             )
#             logger.info(f"Payment initiated for user {request.user.id} with tx_ref {tx_ref}.")  # noqa
#             return redirect(response["payment_link"])

#         # Handle initiation failure
#         error_message = response.get("message", "Unable to initiate payment.")  # noqa
#         messages.error(request, error_message)
#         logger.error(f"Failed to initiate payment for user {request.user.id}: {error_message}")  # noqa
#         return render(request, self.template_name)


class FlutterWalletFundView(LoginRequiredMixin, View):
    """Initiates the wallet funding process using Flutterwave."""

    def get(self, request):
        return render(request, "pages/refer/flutterfund_wallet.html")

    def post(self, request):
        amount = request.POST.get("amount")
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except (TypeError, ValueError):
            return HttpResponseBadRequest("Invalid amount specified.")

            # Save original amount in session
        request.session["original_amount"] = amount

        # Fetch the exchange rate for USD to NGN
        try:
            exchange_rate = get_exchange_rate("NGN")
            amount_in_naira = convert_to_naira(amount, exchange_rate)
            # Round the amount to two decimal places
            amount_in_naira = round(amount_in_naira, 2)
        except Exception as e:
            logger.error(f"Error converting amount to Naira: {e}")
            return JsonResponse(
                {
                    "error": "Unable to process conversion at this time."
                }, status=500
            )

        # Initiate payment via Flutterwave
        flutterwave = Flutterwave()
        # Include the original amount (USD) in the tx_ref
        tx_ref = f"funding_{request.user.id}_{timezone.now().timestamp()}_{amount}"   # noqa
        redirect_url = request.build_absolute_uri(
            reverse("referals:flutterwave_callback")
        )
        customer = {
            "email": request.user.email,
            "phonenumber": request.user.phone_no,
            "name": request.user.name,
        }
        payment_response = flutterwave.initiate_payment(
            tx_ref, amount_in_naira, "NGN", customer, redirect_url
        )

        if payment_response["status"] == "success":
            return redirect(payment_response["payment_link"])
        return JsonResponse({"error": payment_response["message"]}, status=400)


class FlutterwaveCallbackView(LoginRequiredMixin, View):
    """Handles the Flutterwave payment callback and wallet crediting."""

    def get(self, request):
        status = request.GET.get("status")
        transaction_id = request.GET.get("transaction_id")

        if status != "successful" or not transaction_id:
            return HttpResponseBadRequest(
                "Payment was not successful or transaction ID missing."
            )

        # Verify payment with Flutterwave
        flutterwave = Flutterwave()
        verification_result = flutterwave.verify_payment(transaction_id)

        if verification_result["status"] == "success":
            # amount = verification_result["amount"]

            # Extract the original amount (USD) from the tx_ref
            original_amount = request.session.get("original_amount")
            if not original_amount:
                logger.error("Original amount not found in session.")
                return HttpResponseBadRequest("Invalid session state.")
            user_wallet = get_object_or_404(Wallet, user=request.user)
            user_wallet.credit_wallet(original_amount)
            logger.info(f"Wallet credited with {original_amount} for user {request.user.id}.")  # noqa
            return redirect("referals:funding_success")

        logger.error(f"Flutterwave callback verification failed for transaction {transaction_id}: {verification_result['message']}")  # noqa
        return JsonResponse({"error": verification_result["message"]}, status=400)  # noqa


class WalletFundingSuccessView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        messages.success(
            request,
            "Your wallet has been successfully funded!"
        )
        return render(request, "pages/refer/funding_success.html")


class WalletFundingCancelView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        messages.warning(request, "Your wallet funding was canceled.")
        return render(request, "pages/refer/funding_cancel.html")


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "pages/refer/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 10  # Number of notifications per page

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unread_count"] = Notification.get_unread_count(
            self.request.user
        )
        return context


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Handles AJAX request to mark all notifications as read."""

    def post(self, request, *args, **kwargs):
        unread_notifications = Notification.objects.filter(
            user=request.user, read=False
        )
        for notification in unread_notifications:
            notification.mark_as_read()  # Use model method
        return JsonResponse({
            "status": "success",
            "message": "All notifications marked as read."
        })


class SMSCampaignListView(ListView):
    model = SMSCampaign
    template_name = "pages/refer/sms_campaign_list.html"
    context_object_name = "campaigns"
    queryset = SMSCampaign.objects.all().order_by("-created_at")

    def get_queryset(self):
        return SMSCampaign.objects.all().order_by("-created_at")


class SMSCampaignDetailView(DetailView):
    model = SMSCampaign
    template_name = "sms_campaign_detail.html"
    context_object_name = "campaign"


class SMSCampaignCreateView(CreateView):
    model = SMSCampaign
    template_name = "sms_campaign_form.html"
    fields = ['name', 'message', 'status']
    success_url = reverse_lazy('sms_campaign_list')

    def form_valid(self, form):
        campaign = form.save(commit=False)  # noqa
        # Optionally handle more logic before saving, e.g., setting the user
        return super().form_valid(form)


class SMSCampaignUpdateView(UpdateView):
    model = SMSCampaign
    template_name = "sms_campaign_form.html"
    fields = ['name', 'message', 'status']
    success_url = reverse_lazy('sms_campaign_list')

    def form_valid(self, form):
        campaign = form.save(commit=False)  # noqa
        # Optionally handle more logic before saving
        return super().form_valid(form)


class SMSCampaignSendView(FormMixin, DetailView):
    model = SMSCampaign
    template_name = "sms_campaign_send.html"
    context_object_name = "campaign"

    def post(self, request, *args, **kwargs):
        campaign = self.get_object()
        if campaign.status == SMSCampaignStatusChoices.DRAFT:
            result = campaign.send_to_users()
            if result:
                return JsonResponse(
                    {"message": "SMS Campaign sent successfully."}
                )
            return JsonResponse(
                {"message": "Failed to send SMS campaign."}, status=500
            )
        return JsonResponse(
            {"message": "Campaign is not in 'Draft' status."}, status=400
        )
