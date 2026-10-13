from django.apps import AppConfig


class ReadifyV2Config(AppConfig):
    """Isolated V2 features; the original database schema remains intact."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "readify.v2"
    label = "readify_v2"
    verbose_name = "Readify V2"
