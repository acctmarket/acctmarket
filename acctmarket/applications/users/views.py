import logging

from allauth.account.utils import send_email_confirmation
from allauth.account.views import LoginView, SignupView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (DetailView, FormView, RedirectView,
                                  TemplateView, UpdateView, View)
from django.views.generic.edit import CreateView

from acctmarket.applications.blog.models import Post
from acctmarket.applications.ecommerce.models import (CartOrder,
                                                      CartOrderItems, Product)
from acctmarket.applications.refer.models import Notification, Referral, Wallet
from acctmarket.applications.users.forms import (CustomSignupForm,
                                                 CustomUserCreationForm,
                                                 OTPVerificationForm)
from acctmarket.applications.users.models import (
    Account, Accountant, Administrator, ContentManager, Customer,
    CustomerSupportRepresentative, User)
from acctmarket.applications.users.services import TwilloSMSService

logger = logging.getLogger(__name__)


class CustomSignupView(SignupView):
    form_class = CustomSignupForm


custom_signup_views = CustomSignupView.as_view()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name", "country", "phone_no", "email"]
    success_message = _("Information successfully updated")
    template_name = "account/user_detail.html"

    def get_success_url(self):
        # for mypy to know that the user is authenticated
        assert self.request.user.is_authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("homeapp:home")


user_redirect_view = UserRedirectView.as_view()


class DashboardView(LoginRequiredMixin, View):
    """
    View to handle dispatching the user to the appropriate dashboard
    based on their role.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == "customer":
            return redirect(reverse("users:customer_dashboard"))
        elif user.role == "content_manager":
            return redirect(reverse(
                "users:content_manager_dashboard")
            )


dashboard_view = DashboardView.as_view()


class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard/customer.html"

    def get_context_data(self, **kwargs):
        """Add additional context data to the customer dashboard view."""
        context = super().get_context_data(**kwargs)

        user = self.request.user
        get_successful_referrals = Referral.get_successful_referrals(user)
        notifications: Notification = Notification.objects.all()
        # Wallet Information
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            wallet = None

        # Referral Information
        customer, created = Customer.objects.get_or_create(user=user)
        # referral, created = Referral.objects.get_or_create(referrer=user)
        referred_user_count = get_successful_referrals.filter(
            referred_user__isnull=False  # Ensure there's a referred user
        ).count
        successful_referrals = get_successful_referrals

        purchased_product_count = CartOrderItems.objects.filter(
            order__user=user,
            order__paid_status=True,
        ).select_related("product", "order").count()

        notifications = notifications.filter(
            user=user, read=False
        )[:5]
        notification_unread_count = Notification.get_unread_count(
            user
        )
        get_customer = Customer.objects.get(
            user=self.request.user
        )

        # Add wallet and referral data to the context
        context["wallet_balance"] = wallet.balance if wallet else 0
        context["referral_code"] = customer.referral_code
        context["referral_link"] = customer.get_referral_link
        context["successful_referrals"] = successful_referrals
        context["referred_user_count"] = referred_user_count
        context["purchased_product_count"] = purchased_product_count
        context["notifications"] = notifications
        context["notification_unread_count"] = notification_unread_count
        context["get_customer"] = get_customer

        return context


customer_dashboard = CustomerDashboardView.as_view()


class ContentManagerDashboard(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard/content_manager.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["all_customers"] = Customer.objects.count()
        context["products"] = Product.objects.count()
        context["orders"] = CartOrder.objects.count()
        context["blogs"] = Post.objects.count()
        return context


content_manager_dashboard = ContentManagerDashboard.as_view()


class BaseSignupView(SignupView):
    """
    A base signup view that handles common functionality
    for all account types.
    This includes creating the user,
    sending email confirmation, and handling
    form errors.
    """
    def form_valid(self, form):
        try:
            with transaction.atomic():
                user = form.save(self.request)
                self.create_account_related_data(user, form)
                send_email_confirmation(self.request, user)
                return HttpResponseRedirect("/accounts/confirm-email/")
        except ValueError:
            form.add_error(
                None,
                "The provided email address is not valid or already in use."
            )
            return self.form_invalid(form)
        except (DatabaseError, ValidationError) as e:
            form.add_error(None, f"An error occurred: {e!s}")
            return self.form_invalid(form)

    def create_account_related_data(self, user, form):
        """
        This method should be overridden by subclasses to handle creating
        role-specific data (e.g., ContentManager, CustomerSupport, etc.)
        """
        raise NotImplementedError(
            "Subclasses must implement this method to handle account-specific logic."  # noqa
        )


class ContentManagerAccount(BaseSignupView):
    form_class = CustomSignupForm
    template_name = "account/content_manager.html"

    def create_account_related_data(self, user, form):
        """
        Create the account and Content Manager-specific data.
        """
        expertise_area = form.cleaned_data.get("expertise_area")
        account, _ = Account.objects.get_or_create(owner=user)
        ContentManager.objects.create(
            user=user,
            account=account,
            expertise_area=expertise_area,
        )


content_manager_account = ContentManagerAccount.as_view()


class AccountantAccount(BaseSignupView):
    form_class = CustomSignupForm
    template_name = "account/accountant_signup.html"

    def create_account_related_data(self, user, form):
        """
        Create the account and Accountant-specific data.
        """
        financial_software_used = form.cleaned_data.get(
            "financial_software_used"
        )
        account, _ = Account.objects.get_or_create(owner=user)
        Accountant.objects.create(
            user=user,
            account=account,
            financial_software_used=financial_software_used

        )


accountant_account = AccountantAccount.as_view()


class AdministratorAccount(SignupView):
    form_class = CustomSignupForm
    template_name = "account/administrator.html"

    def form_valid(self, form):
        user = form.save(self.request)  # Use form.save() to get the user instance     # noqa
        department = form.cleaned_data.get("department")

        # Get or create the associated account for the user
        account, created = Account.objects.get_or_create(owner=user)

        # Create the Administrator instance with the associated account
        Administrator.objects.create(
            user=user, account=account, department=department)

        # Send email confirmation
        send_email_confirmation(self.request, user)

        return HttpResponseRedirect(
            "/accounts/confirm-email/",
        )  # Redirect after successful signup


administrator_account = AdministratorAccount.as_view()


class CustomerSupportRepresentativeAccount(SignupView):
    form_class = CustomSignupForm
    template_name = "account/customer_reps.html"

    def form_valid(self, form):
        try:
            user = form.save(self.request)
            department = form.cleaned_data.get("department")

            account, created = Account.objects.get_or_create(owner=user)
            CustomerSupportRepresentative.objects.create(
                user=user,
                account=account,
                department=department,
            )

            send_email_confirmation(self.request, user)
            return HttpResponseRedirect("/accounts/confirm-email/")
        except ValueError as e:                       # noqa
            # Handle the case where the email address is causing a ValueError
            form.add_error(
                None,
                "The provided email address is not valid or already in use."
            )           # noqa
            return self.form_invalid(form)
        except (DatabaseError, ValidationError) as e:
            form.add_error(None, f"An error occurred: {e!s}")
            return self.form_invalid(form)


customer_support_reps = CustomerSupportRepresentativeAccount.as_view()


class CustomerAccount(BaseSignupView):
    form_class = CustomSignupForm
    template_name = "account/customer_account.html"

    def get_initial(self):
        """Set initial data for the form, including any referral code."""
        initial = super().get_initial()
        referral_code = self.request.GET.get("referral_code")
        if referral_code:
            initial["referral_code"] = referral_code
        return initial

    def create_account_related_data(self, user, form):
        """
        Create account and customer data for a new user.
        Handle referral logic based on the referral code.
        """
        # Create or get the associated account
        account, _ = Account.objects.get_or_create(owner=user)

        # Safely create or get the customer profile
        for _ in range(5):  # Retry up to 5 times for uniqueness
            try:
                customer, created = Customer.objects.get_or_create(
                    user=user, account=account
                )
                if created:
                    customer.referral_code = Customer.generate_referral_code()
                    customer.save()
                break
            except IntegrityError:
                continue  # Retry with a new referral code
        else:
            messages.error(
                self.request,
                "Failed to generate a unique referral code."
            )
            return

        # Referral logic
        referral_code = self.request.GET.get("referral_code")
        if referral_code:
            try:
                referrer = Customer.objects.get(referral_code=referral_code)

                # Associate the new customer with the referrer
                customer.referred_by = referrer
                customer.save()

                # Notify the referrer
                referrer.notify_referrer()

                # Update or create a referral entry
                for _ in range(5):  # Retry up to 5 times
                    try:
                        logger.info(
                            f"Creating Referral: referrer={referrer.user}, referred_user={user}"    # noqa
                        )
                        Referral.objects.update_or_create(
                            referrer=referrer.user,
                            referred_user=user,
                            defaults={
                                # "referral_code": referral_code,
                                "referred_user_signup_completed": True,
                            },
                        )
                        logger.info("Referral created/updated successfully.")
                        break
                    except IntegrityError as e:
                        logger.error(
                            f"IntegrityError during Referral creation: {str(e)}"  # noqa
                        )  # Log the error
                        continue  # Retry if a race condition or conflict occurs  # noqa
                else:
                    messages.error(
                        self.request,
                        "Failed to create a referral entry after multiple attempts."  # noqa
                    )
            except Customer.DoesNotExist:
                messages.error(
                    self.request,
                    "Invalid or expired referral code."
                )

    def form_valid(self, form):
        """
        Save the user, handle referral and account creation,
        and send OTP for phone verification if available.
        """
        try:
            with transaction.atomic():
                # Save user and create account-related data
                user = form.save(self.request)
                self.create_account_related_data(user, form)

                # Update the customer's SMS opt-in preference
                customer = Customer.objects.get(user=user)
                customer.sms_opt_in = form.cleaned_data.get(
                    "sms_opt_in", False
                )
                customer.save()

                # Send OTP if phone number is provided
                if user.phone_no:
                    send_otp = TwilloSMSService()
                    send_otp.send_otp_via_sms(user)
                    messages.success(
                        self.request,
                        "OTP has been sent to your phone number."
                    )
                    return redirect(
                        reverse(
                            "users:verify_otp", kwargs={"user_id": user.id}
                        )
                    )
                else:
                    messages.error(
                        self.request,
                        "Please provide a valid phone number."
                    )
                    return self.form_invalid(form)

        except ValueError:
            form.add_error(
                None,
                "The provided email address is not valid or already in use."
            )
            return self.form_invalid(form)

        # except (DatabaseError, ValidationError) as e:
        #     form.add_error(None, f"An unexpected error occurred: {str(e)}")
        #     return self.form_invalid(form)


customers_account = CustomerAccount.as_view()


class SuperuserSignupView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "account/superuser_signup.html"
    success_url = reverse_lazy('admin:login')

    def form_valid(self, form):
        # Set the necessary fields for superuser
        form.instance.is_staff = True
        form.instance.is_superuser = True
        return super().form_valid(form)


superuser = SuperuserSignupView.as_view()


# class RequestOtp(View):
#     """
#     Handles OTP request for a user.
#     """
#     def get(self, request, user_id, *args, **kwargs):
#         try:
#             user = User.objects.get(pk=user_id)
#             if user.phone_no:
#                 # Send OTP via SMS
#                 send_otp_via_sms(user)
#                 messages.success(
#                     request, "OTP has been sent to your phone number."
#                 )
#                 return redirect(
#                     reverse('verify_otp', kwargs={'user_id': user_id})
#                 )
#             else:
#                 messages.error(request, "No phone number provided.")
#                 return redirect(reverse('register'))

#         except User.DoesNotExist:
#             return HttpResponse(status=404)


# request_otp = RequestOtp.as_view()


class VerifyOTPView(FormView):
    """
    Handles OTP verification for a user.
    """
    template_name = "account/verify_otp.html"
    form_class = OTPVerificationForm

    def form_valid(self, form):
        user_id = self.kwargs["user_id"]
        otp_code = form.cleaned_data["otp"]

        try:
            user = User.objects.get(pk=user_id)

            # Verify OTP logic
            if user.verify_otp(otp_code):
                # Send email confirmation if OTP is valid
                send_email_confirmation(self.request, user)
                messages.success(
                    self.request,
                    "Phone number verified successfully!"
                )
                user.phone_verified = True
                user.save()

                # Redirect to email confirmation page
                send_email_confirmation(self.request, user)
                return HttpResponseRedirect("/accounts/confirm-email/")
            else:
                messages.error(
                    self.request, "Invalid or expired OTP. Please try again."
                )
                return redirect(
                    reverse(
                        "users:verify_otp", kwargs={"user_id": user_id}
                    )
                )

        except User.DoesNotExist:
            return HttpResponse(status=404)

    def process_referral(self, user, referral_code):
        """
        Processes the referral for the newly registered and verified user.
        Links the referred_user to the referrer and marks the referral as
        complete.
        """
        try:
            with transaction.atomic():
                # Retrieve referral by referral code
                referral = Referral.objects.get(referral_code=referral_code)

                # Link the user as the referred_user and mark the referral as complete  # noqa
                referral.referred_user = user
                referral.is_completed = True
                referral.save()

                # Placeholder: Update referrer's wallet or notify referrer
                # Example:
                # wallet = Wallet.objects.get(user=referral.referrer)
                # wallet.balance += referral_bonus_amount
                # wallet.save()
                # referral.notify_referrer()

        except Referral.DoesNotExist:
            messages.warning(self.request, "Invalid referral code.")
        except ValidationError as e:
            messages.warning(self.request, str(e))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = User.objects.get(pk=self.kwargs["user_id"])
        return context


verify_otp = VerifyOTPView.as_view()


class ResendOTPView(View):
    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
            if user.phone_no:
                # calling the  method to send OTP
                send_otp = TwilloSMSService()
                send_otp.send_otp_via_sms(user)
                messages.success(
                    request,
                    "OTP has been resent to your phone number."
                )
            else:
                messages.error(
                    request,
                    "User does not have a valid phone number."
                )
        except User.DoesNotExist:
            return HttpResponse(status=404)

        return redirect(
            reverse("users:verify_otp", kwargs={"user_id": user_id})
        )


resend_otp = ResendOTPView.as_view()


class CustomLoginView(LoginView):
    def form_valid(self, form):
        user = form.user

        # Check if the user has a Customer profile and `phone_verified`
        is_customer = Customer.objects.filter(user=user).exists()
        if is_customer:
            print(f"User {user} is a customer.")  # Debug statement
            if not user.phone_verified:
                messages.error(
                    self.request,
                    "Your phone number is not verified. Please verify your phone to continue."   # noqa
                )
                return redirect("users:verify_otp", user_id=user.id)
            else:
                print("Phone number verified. Proceeding with login.")

        return super().form_valid(form)

# custom_login = CustomLoginView.as_view()
