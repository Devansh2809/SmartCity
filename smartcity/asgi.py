import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartcity.settings')

import django  # noqa: E402
django.setup()

from django.core.asgi import get_asgi_application  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
import incidents.routing  # noqa: E402

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            incidents.routing.websocket_urlpatterns
        )
    ),
})
