from django.apps import AppConfig

class MainappConfig(AppConfig):
    name = 'mainapp'

    def ready(self):
        # import signals to register them
        import mainapp.signals  # noqa
