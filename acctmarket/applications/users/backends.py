
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class MyAuthenticationBackend(ModelBackend):
    def authenticate(self, request, **credentials):
        user = super().authenticate(request, **credentials)

        if user is not None:
            if not user.phone_verified:
                return None  # Deny login for unverified users
        return user
