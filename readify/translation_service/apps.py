from django.apps import AppConfig


class TranslationServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'readify.translation_service'
    verbose_name = '翻译服务' 