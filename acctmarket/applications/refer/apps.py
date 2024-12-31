from django.apps import AppConfig


class ReferConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "acctmarket.applications.refer"

    def ready(self):
        try:
            import acctmarket.applications.refer.signals  # noqa F401
        except ImportError:
            pass
