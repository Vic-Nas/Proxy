"""Simple configuration - load service mappings from environment."""
import os

# Load service mappings from environment variables
# Format: SERVICE_name=target.domain.com
SERVICES = {}
for key, value in os.environ.items():
    if key.startswith('SERVICE_'):
        service_name = key.replace('SERVICE_', '')
        # Skip duplicates (take first occurrence)
        if service_name in SERVICES:
            print(f"[WARNING] Duplicate service '{service_name}' ignored (keeping first: {SERVICES[service_name]})")
            continue
        SERVICES[service_name] = value

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Feature flags
SHOW_FIXES = os.environ.get('FIXES', 'false').lower() == 'true'

# Coffee button settings
COFFEE_USERNAME = os.environ.get('COFFEE_USERNAME', 'vicnas')
SHOW_COFFEE = os.environ.get('COFFEE', 'true').lower() == 'true'

# Logs service - if LOGS=true, adds a /_logs/ service
ENABLE_LOGS = os.environ.get('LOGS', 'false').lower() == 'true'
if ENABLE_LOGS:
    SERVICES['_logs'] = 'internal-logs'  # Special marker for logs service

BLOCKED_SERVICES = ['www', 'mail', 'ftp', 'ssh']