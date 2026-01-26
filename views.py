from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re
from config import TARGET_DOMAIN_PATTERN, ALLOWED_SERVICES, BLOCKED_SERVICES


def home(request):
    """Simple status page showing the proxy is running."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Reverse Proxy</title></head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 50px auto;">
        <h1>🔄 Reverse Proxy Active</h1>
        <p>This service proxies requests to backend services.</p>
        <p><strong>Usage:</strong> <code>/{service}/{path}</code></p>
        <p><strong>Example:</strong> <code>/api/users</code> → <code>https://api.up.railway.app/users</code></p>
    </body>
    </html>
    """
    return HttpResponse(html)


@csrf_exempt
def proxy_view(request, service, path=''):
    """
    Proxy requests to backend services.
    
    Args:
        service: The service name (e.g., 'api', 'web')
        path: The path after the service name
    """
    # Validate service name
    if BLOCKED_SERVICES and service in BLOCKED_SERVICES:
        return JsonResponse({'error': f'Service "{service}" is blocked'}, status=403)
    
    if ALLOWED_SERVICES and service not in ALLOWED_SERVICES:
        return JsonResponse({'error': f'Service "{service}" is not allowed'}, status=403)
    
    # Build target URL
    target_domain = TARGET_DOMAIN_PATTERN.format(service=service)
    url = f"https://{target_domain}/{path}"
    
    # Preserve query string
    if request.META.get('QUERY_STRING'):
        url += f"?{request.META['QUERY_STRING']}"
    
    print(f"[PROXY] {request.method} /{service}/{path} → {url}")
    
    try:
        # Prepare request
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in ['connection', 'cookie', 'host']
        }
        headers.update({
            'Host': target_domain,
            'X-Forwarded-Host': request.get_host(),
            'X-Forwarded-Proto': 'https' if request.is_secure() else 'http',
            'X-Real-IP': request.META.get('REMOTE_ADDR', ''),
        })
        
        # Forward cookies
        cookies = {key: value for key, value in request.COOKIES.items()}
        
        # Make the proxied request
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.body,
            cookies=cookies,
            allow_redirects=False,
            timeout=30
        )
        
        content_type = resp.headers.get('content-type', '')
        
        # Rewrite content based on type
        if 'text/html' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_html(content, service)
            response = HttpResponse(content, status=resp.status_code)
        elif 'javascript' in content_type or 'application/json' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_javascript(content, service)
            response = HttpResponse(content, status=resp.status_code)
        else:
            response = HttpResponse(resp.content, status=resp.status_code)
        
        # Copy response headers
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    value = rewrite_location(value, service, target_domain)
                response[key] = value
        
        # Handle cookies
        if 'Set-Cookie' in resp.headers:
            for cookie in resp.raw.headers.getlist('Set-Cookie'):
                cookie = rewrite_cookie(cookie, service)
                response['Set-Cookie'] = cookie
        
        return response
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout connecting to {url}")
        return JsonResponse({'error': 'Backend service timeout'}, status=504)
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Connection error: {e}")
        return JsonResponse({'error': 'Cannot connect to backend service'}, status=502)
    except Exception as e:
        print(f"[ERROR] Proxy error: {e}")
        return JsonResponse({'error': 'Proxy error', 'details': str(e)}, status=502)


def rewrite_html(content, service):
    """Rewrite HTML content to fix URLs."""
    # Rewrite href, src, action attributes
    content = re.sub(r'(href|src|action)="(/[^"]*)"', rf'\1="/{service}\2"', content)
    content = re.sub(r"(href|src|action)='(/[^']*)'", rf"\1='/{service}\2'", content)
    
    # Rewrite fetch() calls
    content = re.sub(r'fetch\s*\(\s*["\'](/[^"\']+)', rf'fetch("/{service}\1', content)
    
    return content


def rewrite_javascript(content, service):
    """Rewrite JavaScript content to fix URLs."""
    # Rewrite common JS patterns
    content = re.sub(
        r'(fetch|ajax|url:\s*|xhr\.open\([^,]+,\s*)(["\'])(/[a-zA-Z][^"\']*)',
        rf'\1\2/{service}\3',
        content
    )
    return content


def rewrite_location(location, service, target_domain):
    """Rewrite Location header for redirects."""
    if location.startswith('/'):
        return f'/{service}{location}'
    elif location.startswith(f'https://{target_domain}/'):
        return location.replace(f'https://{target_domain}/', f'/{service}/')
    return location


def rewrite_cookie(cookie, service):
    """Rewrite cookie to work with the proxy."""
    # Remove Domain restriction
    cookie = re.sub(r';\s*Domain=[^;]+', '', cookie, flags=re.IGNORECASE)
    # Update Path
    cookie = re.sub(r'(Path=)(/[^;]*)', rf'\1/{service}\2', cookie, flags=re.IGNORECASE)
    return cookie