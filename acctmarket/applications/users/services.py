import logging

from django.conf import settings
from twilio.rest import Client

from acctmarket.applications.users.models import User

logger = logging.getLogger(__name__)


class TwilloSMSService:
    def __init__(self):
        # Create Twilio client using credentials from settings
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )

    def send_otp_via_sms(self, user: User):
        """
        Generates and sends an OTP via SMS to the user's phone number
        using Twilio.

        Args:
            user: The user object for which the OTP will be generated and sent.

        Returns:
            The message SID from Twilio as confirmation of
            successful message dispatch.
        """

        otp = (
            user.generate_otp()
        )  # Call the OTP generation method on the user model  # noqa

        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)  # noqa

        # Send the SMS with the generated OTP
        message = self.client.messages.create(
            body=f"Your OTP for phone verification is {otp}",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=str(user.formatted_phone_number),
        )

        # Return the SID of the message for logging/tracking purposes
        return message.sid

    def send_sms(self, to, message):
        """
        Send a single SMS to a specific recipient.
        """
        try:
            message = self.client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to,
            )
            return {"sid": message.sid, "status": message.status}
        except Exception as e:
            # Handle SMS sending errors
            logger.error(f"Failed to send SMS: {e}")
            return None

    def send_bulk_sms(self, recipients, message):
        """
        Send bulk SMS to multiple recipients.
        """
        if not isinstance(recipients, list) or not all(
            isinstance(r, str) for r in recipients
        ):  # noqa
            logger.error("Recipients must be a list of phone numbers.")
            raise ValueError(
                "Recipients must be a list of valid phone numbers."
            )
        results = []
        for recipient in recipients:
            result = self.send_sms(recipient, message)
            results.append({"recipient": recipient, "result": result})
            logger.info(
                f"Bulk SMS process completed. Sent to {len(recipients)} recipients."  # noqa
            )  # noqa
        return results
