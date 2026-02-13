"""Simple configuration - load service mappings from environment."""
import os
import glob

# Load service mappings from environment variables
# Format: SERVICE_name=target.domain.com or SERVICE_name=target.domain.com/base/path
# Optional: SERVICE_name_DESC=description, SERVICE_name_RANK=number
SERVICES = {}
SERVICE_BASE_PATHS = {}
SERVICE_DESCRIPTIONS = {}
SERVICE_RANKS = {}
SERVICE_HIDDEN = {}
LOCAL_TEMPLATES = {}  # Maps service name to template filename

# Auto-detect local templates
def load_local_templates():
    """Scan templates folder for .html files (excluding home, 404, error)."""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    excluded = ['home.html', '404.html', 'error.html']
    
    if os.path.exists(templates_dir):
        for template_file in glob.glob(os.path.join(templates_dir, '*.html')):
            filename = os.path.basename(template_file)
            if filename not in excluded:
                # Extract service name from filename (e.g., about.html -> about)
                service_name = os.path.splitext(filename)[0]
                LOCAL_TEMPLATES[service_name] = filename

# Load templates first
load_local_templates()

# Load environment-based services
for key, value in os.environ.items():
    if key.startswith('SERVICE_') and not key.endswith('_DESC') and not key.endswith('_RANK'):
        service_name = key.replace('SERVICE_', '')
        
        # If this service has an env var, it overrides any local template
        if service_name in LOCAL_TEMPLATES:
            print(f"[INFO] SERVICE_{service_name} env var overrides local template {LOCAL_TEMPLATES[service_name]}")
            del LOCAL_TEMPLATES[service_name]
        
        # Skip duplicates (take first occurrence)
        if service_name in SERVICES:
            print(f"[WARNING] Duplicate service '{service_name}' ignored (keeping first: {SERVICES[service_name]})")
            continue
        
        # Split domain and base path
        if '/' in value:
            parts = value.split('/', 1)
            SERVICES[service_name] = parts[0]
            SERVICE_BASE_PATHS[service_name] = '/' + parts[1]
        else:
            SERVICES[service_name] = value
            SERVICE_BASE_PATHS[service_name] = ''
        
        # Load optional description
        desc_key = f'SERVICE_{service_name}_DESC'
        if desc_key in os.environ:
            SERVICE_DESCRIPTIONS[service_name] = os.environ[desc_key]
        
        # Load optional rank (default to 999 for unranked)
        rank_key = f'SERVICE_{service_name}_RANK'
        if rank_key in os.environ:
            try:
                SERVICE_RANKS[service_name] = int(os.environ[rank_key])
            except ValueError:
                SERVICE_RANKS[service_name] = 999
        else:
            SERVICE_RANKS[service_name] = 999
        # Load optional hide flag (default: visible)
        hide_key = f'SERVICE_{service_name}_HIDE'
        # If set to 'true' (case-insensitive) the service will be hidden from homepage
        SERVICE_HIDDEN[service_name] = os.environ.get(hide_key, 'false').lower() == 'true'

# Add local templates as services with lower priority (rank 1000)
for service_name, template_file in LOCAL_TEMPLATES.items():
    SERVICES[service_name] = f'local-template:{template_file}'
    SERVICE_BASE_PATHS[service_name] = ''
    SERVICE_RANKS[service_name] = 1000
    # Local templates default to visible unless overridden
    SERVICE_HIDDEN[service_name] = os.environ.get(f'SERVICE_{service_name}_HIDE', 'false').lower() == 'true'
    # Description defaults to empty unless there's a comment in the template

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Coffee button settings
COFFEE_USERNAME = os.environ.get('COFFEE_USERNAME', 'vicnas')
SHOW_COFFEE = os.environ.get('COFFEE', 'true').lower() == 'true'

BLOCKED_SERVICES = ['www', 'mail', 'ftp', 'ssh']

BLOCKED_SERVICES = ['www', 'mail', 'ftp', 'ssh']