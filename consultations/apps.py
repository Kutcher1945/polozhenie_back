from django.apps import AppConfig


class ConsultationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "consultations"
    verbose_name = "Консультации"

    def ready(self):
        """Register signals when app is ready"""
        import consultations.signals