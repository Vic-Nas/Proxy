import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import re_path
from consumers import ProxyWebSocketConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter([
            # Match WebSocket URLs: /service/ws/path or /ws/service/path
            re_path(r'^(?P<service>[a-zA-Z0-9-_]+)/ws/(?P<path>.*)$', ProxyWebSocketConsumer.as_asgi()),
            re_path(r'^ws/(?P<service>[a-zA-Z0-9-_]+)/(?P<path>.*)$', ProxyWebSocketConsumer.as_asgi()),
        ])
    ),
})