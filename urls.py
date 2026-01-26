from django.urls import path, re_path
from django.http import HttpResponse
from views import proxy_view, home

urlpatterns = [
    path('favicon.ico', lambda r: HttpResponse(status=204)),
    re_path(r'^(?P<service>[a-zA-Z0-9-_]+)/(?P<path>.*)$', proxy_view),
    path('', home),
]