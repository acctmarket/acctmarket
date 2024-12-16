import logging
import time
from decimal import Decimal

import requests
from django.conf import settings
# from django.contrib import messages
from django.urls import reverse

logger = logging.getLogger(__name__)


class PayStack:
    PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
    base_url = "https://api.paystack.co"

    def verify_payment(self, ref, *args, **kwargs):
        path = f"/transaction/verify/{ref}"

        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        url = self.base_url + path
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            return response_data["status"], response_data["data"]
        response_data = response.json()
        return response_data["status"], response_data["message"]


class NowPayment:
    """
    Handles interactions with the NOWPayments API,
    including creating payments and verifying payment status.
    """

    def __init__(
        self,
        callback_url_name="referals:nowpayment_callback",
        success_url_name="referals:funding_success",
        cancel_url_name="referals:funding_cancel",
    ):
        # Determine whether to use sandbox or live API
        if settings.USE_NOWPAYMENTS_SANDBOX:
            self.api_key = settings.NOWPAYMENTS_SANDBOX_API_KEY
            self.api_url = settings.NOWPAYMENTS_SANDBOX_API_URL
        else:
            self.api_key = settings.NOWPAYMENTS_API_KEY
            self.api_url = settings.NOWPAYMENTS_API_URL

        # URLs for success, cancel, and callback (customizable per use case)
        self.callback_url_name = callback_url_name
        self.success_url_name = success_url_name
        self.cancel_url_name = cancel_url_name

    def create_payment(self, amount, currency, order_id, description, request):
        """
        Creates a payment invoice using the NOWPayments API.
        """
        url = f"{self.api_url}/invoice"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        data = {
            "price_amount": float(amount),
            "price_currency": currency,
            "order_id": str(order_id),
            "order_description": description,
            "ipn_callback_url": request.build_absolute_uri(
                reverse(self.callback_url_name),
            ),
            "success_url": request.build_absolute_uri(
                reverse(self.success_url_name),
            ),
            "cancel_url": request.build_absolute_uri(
                reverse(self.cancel_url_name),
            ),
        }
        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if response.status_code == 200 and "id" in result:
            return {
                "status": True,
                "data": {
                    "id": int(result["id"]),
                    "invoice_url": result["invoice_url"]
                },
            }

        return {
            "status": False,
            "message": result.get(
                "message",
                "Unknown error",
            ),
        }

    def verify_payment(self, payment_id):
        """
        Verify the payment using the NOWPayments API.
        """
        headers = {
            "x-api-key": self.api_key,
        }
        url = f"{self.api_url}/payment/{payment_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return True, response.json()

        error_message = (
            f"Failed to verify payment: {response.status_code}, {response.text}"  # noqa
        )
        return False, error_message


# class Flutterwave:
#     if settings.USE_FLUTTER_WAVE_TESTING:
#         SECRET_KEY = settings.FLUTTERWAVE_PRIVATE_KEY
#     else:
#         SECRET_KEY = settings.FLUTTERWAVE_SECRET_KEY
#     base_url = "https://api.flutterwave.com/v3/"

#     def initiate_payment(self, data):
#         headers = {
#             "Authorization": f"Bearer {self.SECRET_KEY}",
#             "Content-Type": "application/json",
#         }
#         response = requests.post(
#             # Adjust type if necessary
#             self.base_url + "charges?type=mobilemoneyghana",
#             json=data, headers=headers
#         )

#         # Log the raw response text
#         logging.info(
#             f"Raw response from Flutterwave initiate_payment: {response.text}"  # noqa
#         )

#         try:
#             return response.json()
#         except ValueError:
#             logging.error(f"Error parsing JSON response: {response.text}")
#             return {
#                 "status": "error", "message": "Failed to parse response from Flutterwave."  # noqa
#             }

#     def verify_payment(self, tx_ref, expected_amount, expected_currency):
#         headers = {
#             "Authorization": f"Bearer {self.SECRET_KEY}",
#             "Content-Type": "application/json",
#         }

#         response = requests.get(
#             f"{self.base_url}transactions/verify_by_reference?tx_ref={tx_ref}",
#             headers=headers
#         )

#         logging.info(f"Response status code: {response.status_code}")
#         logging.info(f"Response text: {response.text}")
#         logging.info(f"Verifying payment with tx_ref: {tx_ref}")

#         if response.status_code != 200:
#             logging.error(f"Received error response: {response.status_code} - {response.text}")  # noqa
#             return {
#                 "status": "error",
#                 "message": "Failed to verify payment."
#             }

#         try:
#             response_data = response.json()
#         except ValueError:
#             logging.error(f"Error parsing JSON response: {response.text}")
#             return {
#                 "status": "error",
#                 "message": "Failed to parse response from Flutterwave."
#             }

#         logging.info(f"Response data: {response_data}")

#         if 'data' not in response_data:
#             logging.error(f"Response data missing: {response_data}")
#             return {
#                 "status": "error",
#                 "message": "Response data missing from Flutterwave."
#             }

#         data = response_data['data']

#         # Convert and round amounts
#         flutterwave_amount = Decimal(str(data['amount'])).quantize(Decimal('0.01'), rounding=ROUND_DOWN) # noqa
#         expected_amount_decimal = Decimal(expected_amount).quantize(Decimal('0.01'), rounding=ROUND_DOWN)  # noqa

#         if (
#             data['status'] == "successful" and
#             flutterwave_amount == expected_amount_decimal and
#             data['currency'] == expected_currency
#         ):
#             logging.info("Payment verified successfully.")
#             return {
#                 "status": "success",
#                 "message": "Payment verified successfully.",
#                 "data": data
#             }
#         else:
#             logging.warning(
#                 "Payment verification failed: "
#                 f"Status: {data['status']}, "
#                 f"Amount: {flutterwave_amount}, >>>>>..a "
#                 f"Expected Amount: {expected_amount}, <<<<<e "
#                 f"Currency: {data['currency']}"
#             )
#             return {
#                 "status": "error",
#                 "message": "Payment verification failed.",
#                 "data": data
#             }


def get_exchange_rate(target_currency="NGN"):
    """
    Retrieves the exchange rate for a given target
    currency from an external API.

    Args:
        target_currency (str, optional):
        The currency for which to retrieve the exchange rate.
        Defaults to "NGN".

    Returns:
        Decimal: The exchange rate for the target currency.

    Raises:
        Exception: If the exchange rate cannot be retrieved
        or the target currency is not found in the response data.

    """
    url = f"{settings.EXCHANGE_RATE_API_URL}"
    headers = {
        "apikey": settings.EXCHANGE_RATE_API_KEY,
    }
    response = requests.get(url, headers=headers)
    data = response.json()

    if response.status_code == 200 and "conversion_rates" in data:
        rate = data["conversion_rates"].get(target_currency)
        if rate:
            return Decimal(rate)
        logger.error(
            f"Target currency {target_currency} not found in response data"  # noqa
        )
        raise Exception(
            f"Target currency {target_currency} not found in response data"  # noqa
        )
    logger.error(f"Error fetching exchange rate: {data}")
    raise Exception("Error fetching exchange rate")


def convert_to_naira(amount, exchange_rate):
    try:
        # Ensure amount is a Decimal before multiplying
        amount = Decimal(amount)  # Convert to Decimal for accuracy
        return amount * exchange_rate
    except Exception as e:
        logger.error(f"Error converting amount to Naira: {e}")
        return amount  # If there’s an error, return the original amount


# def convert_to_naira(amount, exchange_rate):
#     return amount * exchange_rate


class Flutterwave:
    base_url = "https://api.flutterwave.com/v3/"

    def __init__(self):
        # Determine keys based on environment
        self.secret_key = (
            settings.FLUTTERWAVE_PRIVATE_KEY
            if settings.USE_FLUTTER_WAVE_TESTING
            else settings.FLUTTERWAVE_SECRET_KEY
        )
        self.public_key = (
            settings.FLUTTERWAVE_PUBLIC_KEY_TEST
            if settings.USE_FLUTTER_WAVE_TESTING
            else settings.FLUTTERWAVE_PUBLIC_KEY
        )

        # Set up headers using the chosen secret key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initiate_payment(
            self, tx_ref, amount, currency,
            customer, redirect_url
    ):
        """Initiates a payment with Flutterwave."""
        data = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": redirect_url,
            "customer": {
                "email": customer.get("email"),
                "phonenumber": customer.get("phonenumber"),
                "name": customer.get("name"),
            },
            "customizations": {
                "title": "Wallet Funding",
                "description": "Fund your wallet using Flutterwave",
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}payments",
                headers=self.headers,
                json=data,
            )
            response_json = response.json()
            logger.info(f"Initiate payment response: {response_json}")

            # Parse the response
            response_json = response.json()
            if response_json.get("status") == "success":
                return {
                    "status": "success",
                    "payment_link": response_json["data"]["link"],
                }
            logger.error(
                f"Payment initiation failed: {response_json.get('message', 'Unknown error')}"  # noqa
            )
            return {
                "status": "error",
                "message": response_json.get(
                    "message",
                    "Unable to initiate payment.",
                ),
            }
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request error during payment initiation: {e}",
            )
            return {
                "status": "error",
                "message": "Network error or invalid response from Flutterwave.",  # noqa
            }

    def verify_payment(self, transaction_id, max_retries=3):
        """Verifies a payment status by transaction ID, with retry logic."""
        verify_url = f"{self.base_url}transactions/{transaction_id}/verify"

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    verify_url,
                    headers=self.headers,
                )
                response_data = response.json()
                logger.info(
                    f"Verification attempt {attempt + 1} for transaction {transaction_id}: {response_data}"  # noqa
                )

                if (
                    response.status_code == 200
                    and response_data["status"] == "success"
                    and response_data["data"]["status"] == "successful"
                ):  # noqa
                    return {
                        "status": "success",
                        "amount": response_data["data"]["amount"],
                    }

                if (
                    response_data.get("message")
                    == "No transaction was found for this id"
                ):  # noqa
                    logger.warning(
                        "Transaction not found on Flutterwave - retrying."
                    )
                    time.sleep(2)  # Wait before retrying
                    continue  # Retry if transaction not found

                return {
                    "status": "error",
                    "message": "Payment verification failed.",
                }

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error during verification for transaction {transaction_id}: {e}"  # noqa
                )  # noqa

        logger.error(
            f"Verification failed after {max_retries} attempts for transaction {transaction_id}"  # noqa
        )  # noqa
        return {
            "status": "error",
            "message": "Verification failed after retries.",
        }
