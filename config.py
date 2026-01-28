"""Simple configuration - load service mappings from environment."""
import os

# Load service mappings from environment variables
# Format: SERVICE_name=target.domain.com
SERVICES = {}
for key, value in os.environ.items():
    if key.startswith('SERVICE_'):
        service_name = key.replace('SERVICE_', '')
        SERVICES[service_name] = value

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Coffee button settings
COFFEE_USERNAME = os.environ.get('COFFEE_USERNAME', 'vicnas')
SHOW_COFFEE = os.environ.get('COFFEE', 'true').lower() == 'true'

BLOCKED_SERVICES = ['www', 'mail', 'ftp', 'ssh']