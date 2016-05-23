from django.apps import AppConfig


class ForumConfig(AppConfig):
    name = 'slimbb'

    def ready(self):
        from . import signals  # NOQA
