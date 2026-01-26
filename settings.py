import os
from config import SECRET_KEY, DEBUG, ALLOWED_HOSTS

SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)
DEBUG = os.environ.get('DEBUG', str(DEBUG)).lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', ','.join(ALLOWED_HOSTS)).split(',')

INSTALLED_APPS = []

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'urls'
DATABASES = {}

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