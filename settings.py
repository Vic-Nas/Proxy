import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = False
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = []

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'urls'
DATABASES = {}

# Add logging
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