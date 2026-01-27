import os
from config import SECRET_KEY, DEBUG, ALLOWED_HOSTS

SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)
DEBUG = os.environ.get('DEBUG', str(DEBUG)).lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', ','.join(ALLOWED_HOSTS)).split(',')

INSTALLED_APPS = [
    'channels',
]

ASGI_APPLICATION = 'routing.application'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'urls'
DATABASES = {}

# Security settings for HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}