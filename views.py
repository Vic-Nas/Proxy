from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import requests

from config import SERVICES, SERVICE_BASE_PATHS, BLOCKED_SERVICES
from utils.version import get_version
from utils.logging import log
from utils.templates import render_template, service_not_found, error_page
from utils.home import render_home
from utils.logs import render_logs
from utils.proxy import (
    build_target_url, make_proxy_request, handle_404_response, 
    process_response_content, copy_response_headers, apply_cache_headers, 
    handle_set_cookies
)

# Import version info
try:
    from version import __name__ as app_name
except ImportError:
    app_name = "Flashy"

__version__ = get_version()


def home(request):
    """Show available services on homepage."""
    return render_home(app_name, __version__)

def logs_view(request):
    """Show recent logs page."""
    return render_logs()


@csrf_exempt
def proxy_view(request, service, path=''):
    """Main proxy logic - forwards requests to backend services or serves local templates."""
    
    # Handle internal logs service
    if service == '_logs':
        return logs_view(request)
    
    # Block reserved service names
    if service in BLOCKED_SERVICES:
        return JsonResponse({'error': 'Blocked'}, status=403)
    
    # Only allow explicitly defined services
    if service not in SERVICES:
        return service_not_found(service, "Service not configured")
    
    target_domain = SERVICES[service]
    
    # Check if this is a local template
    if target_domain.startswith('local-template:'):
        return __handle_local_template(service, target_domain, path, request)
    
    # Continue with normal proxy logic for external services
    return __handle_proxy_request(service, target_domain, path, request)


def __handle_local_template(service, target_domain, path, request):
    """Handle local template rendering."""
    from django.http import HttpResponseRedirect
    
    template_file = target_domain.replace('local-template:', '')
    
    # Local templates only serve the root path
    if path and path != '/':
        return HttpResponse("Local templates only available at root path", status=404)
    
    # Ensure trailing slash
    if not request.path.endswith('/'):
        return HttpResponseRedirect(f'/{service}/')
    
    log(f"[LOCAL] Serving template: {template_file}")
    
    try:
        # Render the local template with basic context
        html = render_template(template_file, {
            'app_name': app_name,
            'version': __version__,
            'service': service,
        })
        return HttpResponse(html)
    except Exception as e:
        log(f"[ERROR] Failed to render template {template_file}: {e}")
        return error_page(
            '❌ Template Error',
            f'Could not render local template: {template_file}',
            f'Error: {str(e)}',
            service=service,
            target=template_file,
            status=500
        )


def __handle_proxy_request(service, target_domain, path, request):
    """Handle proxy request to external service."""
    # Ensure trailing slash for service root
    if not path or path == '/':
        if not request.path.endswith('/'):
            return HttpResponseRedirect(f'/{service}/')
        path = ''
    
    # Build target URL
    base_path = SERVICE_BASE_PATHS.get(service, '')
    url = build_target_url(target_domain, base_path, path, request.META.get('QUERY_STRING'))
    
    try:
        # Make request to backend
        resp = make_proxy_request(service, target_domain, base_path, path, request, url)
        
        # Handle 404s from backend
        if resp.status_code == 404:
            return handle_404_response(resp, path, service, target_domain)
        
        # Get content and content type
        content = resp.content
        content_type = resp.headers.get('content-type', '')
        
        # Process content (rewrite URLs if needed)
        processed_content, is_text = process_response_content(content, content_type, service, target_domain, url)
        
        # Create response
        response = HttpResponse(processed_content, status=resp.status_code)
        
        # Copy headers from backend
        copy_response_headers(resp, response, service, target_domain)
        apply_cache_headers(response)
        handle_set_cookies(resp, response)
        
        return response
        
    except requests.exceptions.Timeout:
        return error_page(
            '⏱️ Backend Timeout',
            'The backend service took too long to respond.',
            'HTTP 504 Gateway Timeout',
            service=service,
            target=target_domain,
            status=504
        )
    except requests.exceptions.ConnectionError:
        return error_page(
            '🔌 Connection Failed',
            'Could not connect to the backend service. The service may be down or unreachable.',
            'HTTP 502 Bad Gateway',
            service=service,
            target=target_domain,
            status=502
        )
    except Exception as e:
        log(f"[ERROR] {e}")
        return error_page(
            '❌ Proxy Error',
            f'An unexpected error occurred while proxying the request.',
            f'Error: {str(e)}',
            service=service,
            target=target_domain,
            status=502
        )
