"""Homepage rendering."""
from django.http import HttpResponse
from config import SERVICES, SERVICE_BASE_PATHS, SERVICE_DESCRIPTIONS, SERVICE_RANKS, SERVICE_HIDDEN, SHOW_COFFEE, COFFEE_USERNAME, DEBUG
from utils.templates import render_template


def build_services_list():
    """Build sorted list of services for display."""
    services_list = []
    for service, domain in SERVICES.items():
        # Skip services marked hidden
        if SERVICE_HIDDEN.get(service, False):
            continue
        base_path = SERVICE_BASE_PATHS.get(service, '')
        
        # Check if this is a local template
        if domain.startswith('local-template:'):
            template_file = domain.replace('local-template:', '')
            full_target = template_file
        else:
            full_target = domain + base_path
        
        description = SERVICE_DESCRIPTIONS.get(service, '')
        rank = SERVICE_RANKS.get(service, 999)
        
        services_list.append({
            'name': service,
            'target': full_target,
            'description': description,
            'rank': rank
        })
    
    # Sort by rank (lower number = higher priority)
    services_list.sort(key=lambda x: x['rank'])
    return services_list


def render_home(app_name, version):
    """Render homepage."""
    html = render_template('home.html', {
        'services': build_services_list(),
        'version': version,
        'app_name': app_name,
        'debug': DEBUG,
        'show_coffee': SHOW_COFFEE,
        'coffee_username': COFFEE_USERNAME,
    })
    return HttpResponse(html)
