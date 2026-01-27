from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import requests
import re
from config import SERVICES, TARGET_DOMAIN_PATTERN, BLOCKED_SERVICES


def home(request):
    """Root path handler."""
    html = """<!DOCTYPE html>
<html>
<head><title>Reverse Proxy</title></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 50px auto;">
<h1>🔄 Proxy Active</h1>
<p>Usage: <code>/{service}/{path}</code></p>
<p>Configured services:</p>
<ul>
"""
    for service, domain in SERVICES.items():
        html += f'<li><code>/{service}/</code> → <code>{domain}</code></li>\n'
    
    html += """</ul>
</body>
</html>"""
    return HttpResponse(html)


@csrf_exempt
def proxy_view(request, service, path=''):
    """Proxy requests to backend services."""
    
    # Block dangerous services
    if service in BLOCKED_SERVICES:
        return JsonResponse({'error': 'Blocked'}, status=403)
    
    # Get target domain from SERVICES or use pattern
    if service in SERVICES:
        target_domain = SERVICES[service]
    else:
        target_domain = TARGET_DOMAIN_PATTERN.format(service=service)
    
    # Handle root service path (e.g., /dash0 or /dash0/)
    if not path or path == '/':
        # Redirect /service to /service/ to maintain consistency
        if not request.path.endswith('/'):
            return HttpResponseRedirect(f'/{service}/')
        path = ''
    
    url = f"https://{target_domain}/{path}"
    
    if request.META.get('QUERY_STRING'):
        url += f"?{request.META['QUERY_STRING']}"
    
    # Simple logging
    if not any(path.endswith(ext) for ext in ['.svg', '.ico', '.css', '.js', '.png', '.jpg']):
        print(f"[PROXY] {request.method} /{service}/{path} → {url}")
    
    try:
        # Prepare headers
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ['connection', 'host']:
                headers[k] = v
        
        # Rewrite headers to backend
        if 'Referer' in headers:
            headers['Referer'] = re.sub(
                rf'https?://[^/]+/{service}/',
                f'https://{target_domain}/',
                headers['Referer']
            )
        
        if 'Origin' in headers:
            headers['Origin'] = f'https://{target_domain}'
        
        headers['Host'] = target_domain
        headers['X-Forwarded-Host'] = request.get_host()
        headers['X-Forwarded-Proto'] = 'https' if request.is_secure() else 'http'
        
        cookies = {key: value for key, value in request.COOKIES.items()}
        
        # Make request
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
        
        # Rewrite HTML/JS content
        if 'text/html' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_content(content, service)
            response = HttpResponse(content, status=resp.status_code)
        elif 'javascript' in content_type or 'application/json' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = rewrite_content(content, service)
            response = HttpResponse(content, status=resp.status_code)
        else:
            response = HttpResponse(resp.content, status=resp.status_code)
        
        # Copy headers
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    # Rewrite redirects
                    if value.startswith('/') and not value.startswith(f'/{service}/'):
                        value = f'/{service}{value}'
                    elif value.startswith(f'https://{target_domain}/'):
                        value = value.replace(f'https://{target_domain}/', f'/{service}/')
                response[key] = value
        
        # Copy cookies
        if 'Set-Cookie' in resp.headers:
            for cookie in resp.raw.headers.getlist('Set-Cookie'):
                response['Set-Cookie'] = cookie
        
        return response
        
    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'Backend timeout'}, status=504)
    except requests.exceptions.ConnectionError:
        return JsonResponse({'error': 'Cannot connect to backend'}, status=502)
    except Exception as e:
        print(f"[ERROR] {e}")
        return JsonResponse({'error': str(e)}, status=502)


def rewrite_content(content, service):
    """Rewrite URLs in content to include service prefix."""
    
    # Fix href/src/action attributes
    content = re.sub(
        r'(href|src|action)="(/(?!' + re.escape(service) + r'/)[^"]+)"',
        rf'\1="/{service}\2"',
        content
    )
    
    # Fix fetch() calls
    content = re.sub(
        r'fetch\s*\(\s*["\'](/(?!' + re.escape(service) + r'/)[^"\']+)["\']',
        rf'fetch("/{service}\1"',
        content
    )
    
    # Fix window.location assignments
    content = re.sub(
        r'(window\.location(?:\.href)?\s*=\s*)["\'](/(?!' + re.escape(service) + r'/)[^"\']+)["\']',
        rf'\1"/{service}\2"',
        content
    )
    
    # Fix JSON paths (for API responses)
    content = re.sub(
        r'"(/(?!' + re.escape(service) + r'/)[a-zA-Z0-9/_-]+)"',
        rf'"/{service}\1"',
        content
    )
    
    return content