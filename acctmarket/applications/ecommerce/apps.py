from django.apps import AppConfig


class EcommerceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "acctmarket.applications.ecommerce"

    def ready(self):
        try:
            import acctmarket.applications.ecommerce.signals  # noqa F401
        except ImportError:
            pass
