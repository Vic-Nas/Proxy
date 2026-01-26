"""
Configuration for the reverse proxy service.
Modify these settings to match your deployment platform and domain pattern.
"""

# Target domain pattern - {service} will be replaced with the service name
# Examples:
#   - Railway: "{service}.up.railway.app"
#   - Render: "{service}.onrender.com"
#   - Fly.io: "{service}.fly.dev"
#   - Custom: "{service}.yourdomain.com"
TARGET_DOMAIN_PATTERN = "{service}.up.railway.app"

# Django settings
SECRET_KEY = 'change-me-in-production'  # Override with environment variable
DEBUG = False
ALLOWED_HOSTS = ['*']

# Optional: List of allowed service names (leave empty to allow all)
# Example: ALLOWED_SERVICES = ['api', 'web', 'admin']
ALLOWED_SERVICES = []

# Optional: Block certain service names
BLOCKED_SERVICES = ['www', 'mail', 'ftp', 'ssh']