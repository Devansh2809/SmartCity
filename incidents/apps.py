from django.apps import AppConfig


class IncidentsConfig(AppConfig):
    name = 'incidents'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import incidents.signals  # noqa: F401

        import sys
        # Only start the background scheduler when the server is actually running.
        # Skip during management commands (migrate, collectstatic, shell, etc.)
        _skip = ('migrate', 'makemigrations', 'collectstatic', 'shell',
                 'test', 'check', 'setup_departments', 'escalate_incidents')
        if any(cmd in sys.argv for cmd in _skip):
            return

        from incidents import scheduler
        scheduler.start()
