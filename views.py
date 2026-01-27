from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re
import json
from config import TARGET_DOMAIN_PATTERN, ALLOWED_SERVICES, BLOCKED_SERVICES


def home(request):
    """Simple status page showing the proxy is running."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reverse Proxy</title>
        <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
    </head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 50px auto;">
        <h1>🔄 Reverse Proxy Active</h1>
        <p>This service proxies requests to backend services.</p>
        <p><strong>Usage:</strong> <code>/{service}/{path}</code></p>
        <p><strong>Example:</strong> <code>/api/users</code> → <code>https://api.up.railway.app/users</code></p>
        <p><strong>WebSocket Support:</strong> Enabled via Django Channels</p>
    </body>
    </html>
    """
    response = HttpResponse(html)
    response['Content-Security-Policy'] = 'upgrade-insecure-requests'
    return response


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
    
    # Only log meaningful requests
    if not any(path.endswith(ext) for ext in ['.svg', '.ico', '.css', '.js', '.png', '.jpg']):
        print(f"[PROXY] {request.method} /{service}/{path}")
    
    try:
        # Prepare request headers
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ['connection', 'host']:
                headers[k] = v
        
        # Rewrite Referer header to point to backend
        if 'Referer' in headers:
            referer = headers['Referer']
            referer = re.sub(
                rf'https?://[^/]+/{service}/',
                f'https://{target_domain}/',
                referer
            )
            headers['Referer'] = referer
        
        # Rewrite Origin header to point to backend
        if 'Origin' in headers:
            headers['Origin'] = f'https://{target_domain}'
        
        # Set required headers
        headers['Host'] = target_domain
        headers['X-Forwarded-Host'] = request.get_host()
        headers['X-Forwarded-Proto'] = 'https' if request.is_secure() else 'http'
        headers['X-Real-IP'] = request.META.get('REMOTE_ADDR', '')
        
        # Forward ALL cookies
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
        if 'application/json' in content_type:
            try:
                content = resp.content.decode('utf-8', errors='ignore')
                data = json.loads(content)
                data = rewrite_json_urls(data, service)
                response = JsonResponse(data, status=resp.status_code, safe=False)
            except (json.JSONDecodeError, Exception):
                response = HttpResponse(resp.content, status=resp.status_code, content_type=content_type)
        elif 'text/html' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_html(content, service)
            response = HttpResponse(content, status=resp.status_code)
            # Add CSP header to upgrade insecure requests in proxied HTML
            response['Content-Security-Policy'] = 'upgrade-insecure-requests'
        elif 'javascript' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_javascript(content, service)
            response = HttpResponse(content, status=resp.status_code)
        elif 'text/css' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_css(content, service)
            response = HttpResponse(content, status=resp.status_code)
        else:
            response = HttpResponse(resp.content, status=resp.status_code)
        
        # Copy response headers
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    value = rewrite_location(value, service, target_domain)
                response[key] = value
        
        # Handle Set-Cookie headers
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


def rewrite_json_urls(data, service):
    """Recursively rewrite URLs in JSON data - ensure HTTPS."""
    if isinstance(data, dict):
        return {key: rewrite_json_urls(value, service) for key, value in data.items()}
    elif isinstance(data, list):
        return [rewrite_json_urls(item, service) for item in data]
    elif isinstance(data, str):
        # Rewrite HTTP to HTTPS in URLs
        data = re.sub(r'http://', 'https://', data)
        # Rewrite if it looks like a path but doesn't already have the service prefix
        if data.startswith('/') and not data.startswith('//') and not data.startswith(f'/{service}/'):
            return f'/{service}{data}'
        return data
    else:
        return data


def rewrite_html(content, service):
    """Rewrite HTML content to fix URLs and enforce HTTPS."""
    # Upgrade HTTP links to HTTPS
    content = re.sub(r'\bhttp://', 'https://', content)
    
    # Add CSP meta tag if not present
    if '<head>' in content and 'Content-Security-Policy' not in content:
        content = content.replace(
            '<head>',
            '<head>\n<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">'
        )
    
    # Rewrite href, src, action attributes (skip if already prefixed)
    content = re.sub(
        r'(href|src|action)="(/(?!' + re.escape(service) + r'/)[^"]+)"',
        rf'\1="/{service}\2"',
        content
    )
    content = re.sub(
        r"(href|src|action)='(/(?!" + re.escape(service) + r"/)[^']+)'",
        rf"\1='/{service}\2'",
        content
    )
    
    # Rewrite fetch() calls (skip if already prefixed)
    content = re.sub(
        r'fetch\s*\(\s*(["\'])(/(?!' + re.escape(service) + r'/)[^"\']+)\1',
        rf'fetch(\1/{service}\2\1',
        content
    )
    
    # Rewrite WebSocket connections - comprehensive approach
    # Pattern 1: new WebSocket('/ws/...')  →  new WebSocket('/{service}/ws/...')
    content = re.sub(
        r'(new\s+WebSocket\s*\(\s*["\'])((?:wss?://)?(?:[^/]+)?)?(/(?!' + re.escape(service) + r'/)[^"\']*?)(["\'])',
        rf'\1/{service}\3\4',
        content
    )
    
    # Pattern 2: WebSocket variable assignments like: const ws = '/ws/...'
    content = re.sub(
        r'(["\'])(/ws/(?!' + re.escape(service) + r'/)[^"\']+)(["\'])',
        rf'\1/{service}\2\3',
        content
    )
    
    # Rewrite template literals (skip if already prefixed)
    def rewrite_template(match):
        path = match.group(1)
        if not path.startswith(f'/{service}/'):
            return f'`/{service}{path}`'
        return match.group(0)
    
    content = re.sub(r'`(/(?!' + re.escape(service) + r'/)[^`]*?)`', rewrite_template, content)
    
    return content


def rewrite_javascript(content, service):
    """Rewrite JavaScript content to fix URLs and enforce HTTPS."""
    # Upgrade HTTP to HTTPS
    content = re.sub(r'\bhttp://', 'https://', content)
    
    # Rewrite fetch() (skip if already prefixed)
    content = re.sub(
        r'fetch\s*\(\s*(["\'])(/(?!' + re.escape(service) + r'/)[^"\']+)\1',
        rf'fetch(\1/{service}\2\1',
        content
    )
    
    # Rewrite xhr.open() (skip if already prefixed)
    content = re.sub(
        r'(xhr\.open\s*\([^,]+,\s*)(["\'])(/(?!' + re.escape(service) + r'/)[^"\']+)\2',
        rf'\1\2/{service}\3\2',
        content
    )
    
    # Rewrite url: property (skip if already prefixed)
    content = re.sub(
        r'(url:\s*)(["\'])(/(?!' + re.escape(service) + r'/)[^"\']+)\2',
        rf'\1\2/{service}\3\2',
        content
    )
    
    # Rewrite window.location (skip if already prefixed)
    content = re.sub(
        r'(window\.location\s*=\s*)(["\'])(/(?!' + re.escape(service) + r'/)[^"\']+)\2',
        rf'\1\2/{service}\3\2',
        content
    )
    content = re.sub(
        r'(window\.location\.href\s*=\s*)(["\'])(/(?!' + re.escape(service) + r'/)[^"\']+)\2',
        rf'\1\2/{service}\3\2',
        content
    )
    
    # Rewrite WebSocket connections - comprehensive
    # Pattern 1: new WebSocket('/ws/...')  →  new WebSocket('/{service}/ws/...')
    content = re.sub(
        r'(new\s+WebSocket\s*\(\s*["\'])((?:wss?://)?(?:[^/]+)?)?(/(?!' + re.escape(service) + r'/)[^"\']*?)(["\'])',
        rf'\1/{service}\3\4',
        content
    )
    
    # Pattern 2: WebSocket variable assignments
    content = re.sub(
        r'(["\'])(/ws/(?!' + re.escape(service) + r'/)[^"\']+)(["\'])',
        rf'\1/{service}\2\3',
        content
    )
    
    # Rewrite template literals (skip if already prefixed)
    def rewrite_template(match):
        path = match.group(1)
        if not path.startswith(f'/{service}/'):
            return f'`/{service}{path}`'
        return match.group(0)
    
    content = re.sub(r'`(/(?!' + re.escape(service) + r'/)[^`]*?)`', rewrite_template, content)
    
    return content


def rewrite_css(content, service):
    """Rewrite CSS content to fix URLs in url() declarations and enforce HTTPS."""
    # Upgrade HTTP to HTTPS
    content = re.sub(r'\bhttp://', 'https://', content)
    
    content = re.sub(r'url\s*\(\s*(["\'])(/[^"\']+)\1\s*\)', rf'url(\1/{service}\2\1)', content)
    content = re.sub(r'url\s*\(\s*(/[^\)]+)\s*\)', rf'url(/{service}\1)', content)
    return content


def rewrite_location(location, service, target_domain):
    """Rewrite Location header for redirects."""
    if location.startswith('/') and not location.startswith('//') and not location.startswith(f'/{service}/'):
        return f'/{service}{location}'
    elif location.startswith(f'https://{target_domain}/'):
        return location.replace(f'https://{target_domain}/', f'/{service}/')
    elif location.startswith(f'http://{target_domain}/'):
        return location.replace(f'http://{target_domain}/', f'/{service}/')
    return location


def rewrite_cookie(cookie, service):
    """Rewrite cookie to work with the proxy - ensure Secure flag."""
    cookie = re.sub(r';\s*Domain=[^;]+', '', cookie, flags=re.IGNORECASE)
    if not re.search(r'Path=', cookie, flags=re.IGNORECASE):
        cookie += f'; Path=/{service}/'
    else:
        cookie = re.sub(r'(Path=)(/[^;]*)', rf'\1/{service}\2', cookie, flags=re.IGNORECASE)
    
    # Add Secure flag if not present
    if not re.search(r';\s*Secure', cookie, flags=re.IGNORECASE):
        cookie += '; Secure'
    
    return cookie