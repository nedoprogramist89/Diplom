from django.apps import AppConfig


class CompetitionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'competitions'
    verbose_name = 'Соревнования'

    def ready(self):
        import competitions.signals  # noqa: F401
