from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import requests
import re
import gzip
import io
from config import SERVICES, TARGET_DOMAIN_PATTERN, BLOCKED_SERVICES


def unknown_service_page(service):
    """Display landing page for unknown services."""
    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>Service Not Found</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 50px auto; color: #666; background: #fafafa; }}
    .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    h1 {{ color: #ff6b6b; margin-top: 0; }}
    .service-name {{ font-family: monospace; color: #0066cc; font-size: 1.1em; }}
    .message {{ color: #666; line-height: 1.6; }}
    a {{ color: #0066cc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .home-link {{ margin-top: 30px; }}
    .home-link a {{ display: inline-block; background: #0066cc; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; }}
    .home-link a:hover {{ background: #0052a3; }}
    .buy-me-coffee {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; }}
    .buy-me-coffee a {{ display: inline-block; background: #ffdd00; color: #000; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; }}
    .buy-me-coffee a:hover {{ background: #ffc800; }}
  </style>
</head>
<body>
<div class="container">
  <h1>⚠️ Service Not Found</h1>
  <p class="message">
    The service <span class="service-name">{service}</span> could not be reached or doesn't exist.
  </p>
  <p class="message">
    Please check that:
  </p>
  <ul style="color: #666;">
    <li>Environment variable <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">SERVICE_{service.upper()}=your-domain.com</code> is defined</li>
    <li>The target service is currently running and accessible</li>
    <li>The domain in SERVICE_{service.upper()} is correct</li>
  </ul>
  
  <div class="home-link">
    <a href="/">← Back to Home</a>
  </div>
  
  <div class="buy-me-coffee">
    <p style="margin-top: 0;">Enjoying this proxy? Support the creator!</p>
    <a href="https://buymeacoffee.com/vicnas" target="_blank">☕ Buy Me A Coffee</a>
  </div>
</div>
</body></html>"""
    return HttpResponse(html, status=404)


def home(request):
    """Root path handler."""
    html = """<!DOCTYPE html>
<html>
<head>
  <title>Reverse Proxy</title>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 50px auto; color: #333; }
    h1 { color: #0066cc; }
    .services { background: #f5f5f5; padding: 15px; border-radius: 8px; }
    .services ul { list-style: none; padding: 0; }
    .services li { padding: 8px 0; }
    .services a { color: #0066cc; text-decoration: none; }
    .services a:hover { text-decoration: underline; }
    .buy-me-coffee { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; }
    .buy-me-coffee a { display: inline-block; background: #ffdd00; color: #000; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; }
    .buy-me-coffee a:hover { background: #ffc800; }
  </style>
</head>
<body>
<h1>🔄 Proxy Active</h1>
<p>Usage: <code>/{service}/{path}</code></p>
"""
    if SERVICES:
        html += '<div class="services"><p>Services:</p><ul>'
        for service, domain in SERVICES.items():
            html += f'<li><a href="/{service}/">{service}</a> → {domain}</li>\n'
        html += "</ul></div>"
    
    html += """<div class="buy-me-coffee">
  <p>Enjoying this proxy? Support the creator!</p>
  <a href="https://buymeacoffee.com/vicnas" target="_blank">☕ Buy Me A Coffee</a>
</div>
</body></html>"""
    return HttpResponse(html)


@csrf_exempt
def proxy_view(request, service, path=''):
    """Proxy requests to backend services."""
    
    if service in BLOCKED_SERVICES:
        return JsonResponse({'error': 'Blocked'}, status=403)
    
    # Get target domain
    if service in SERVICES:
        target_domain = SERVICES[service]
    else:
        target_domain = TARGET_DOMAIN_PATTERN.format(service=service)
        # Test if service exists by making a request
        try:
            test_resp = requests.get(f'https://{target_domain}/', timeout=5, allow_redirects=True)
            # Check if it's a Railway "not found" page
            if test_resp.status_code == 404 or ('Railway' in test_resp.text and 'not found' in test_resp.text.lower()):
                return unknown_service_page(service)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException):
            # Service doesn't exist or is unreachable
            return unknown_service_page(service)
    
    # Handle root service path
    if not path or path == '/':
        if not request.path.endswith('/'):
            return HttpResponseRedirect(f'/{service}/')
        path = ''
    
    url = f"https://{target_domain}/{path}"
    
    if request.META.get('QUERY_STRING'):
        url += f"?{request.META['QUERY_STRING']}"
    
    if not any(path.endswith(ext) for ext in ['.svg', '.ico', '.css', '.js', '.png', '.jpg']):
        print(f"[PROXY] {request.method} /{service}/{path} → {url}")
    
    try:
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ['connection', 'host']:
                headers[k] = v
        
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
        
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.body,
            cookies=cookies,
            allow_redirects=False,
            timeout=30
        )
        
        # Handle content - requests lib auto-decompresses, so just use it directly
        content = resp.content
        content_type = resp.headers.get('content-type', '')
        
        if 'text/html' in content_type:
            text_content = content.decode('utf-8', errors='ignore')
            text_content = rewrite_content(text_content, service)
            response = HttpResponse(text_content, status=resp.status_code)
        elif 'javascript' in content_type or 'application/json' in content_type:
            text_content = content.decode('utf-8', errors='ignore')
            text_content = rewrite_content(text_content, service)
            response = HttpResponse(text_content, status=resp.status_code)
        else:
            response = HttpResponse(content, status=resp.status_code)
        
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    if value.startswith('/') and not value.startswith(f'/{service}/'):
                        value = f'/{service}{value}'
                    elif value.startswith(f'https://{target_domain}/'):
                        value = value.replace(f'https://{target_domain}/', f'/{service}/')
                response[key] = value
        
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
    
    # Fix href/src/action - match "/" exactly or "/something"
    content = re.sub(
        r'(href|src|action)="(/)(?!' + re.escape(service) + r'/)',
        rf'\1="/{service}/',
        content
    )
    content = re.sub(
        r'(href|src|action)="(/(?!' + re.escape(service) + r'/)[^"]*)"',
        rf'\1="/{service}\2"',
        content
    )
    
    # Fix single quotes too
    content = re.sub(
        r"(href|src|action)='(/)(?!" + re.escape(service) + r"/)",
        rf"\1='/{service}/",
        content
    )
    content = re.sub(
        r"(href|src|action)='(/(?!" + re.escape(service) + r"/)[^']*)'",
        rf"\1='/{service}\2'",
        content
    )
    
    # Fix fetch() calls
    content = re.sub(
        r'fetch\s*\(\s*["\']/((?!' + re.escape(service) + r'/)[^"\']*)["\']',
        rf'fetch("/{service}/\1"',
        content
    )
    
    # Fix window.location assignments
    content = re.sub(
        r'window\.location\s*=\s*["\']/((?!' + re.escape(service) + r'/)[^"\']*)["\']',
        rf'window.location="/{service}/\1"',
        content
    )
    content = re.sub(
        r'window\.location\.href\s*=\s*["\']/((?!' + re.escape(service) + r'/)[^"\']*)["\']',
        rf'window.location.href="/{service}/\1"',
        content
    )
    
    # Fix JSON paths (like in API responses)
    content = re.sub(
        r'"/((?!' + re.escape(service) + r'/)[a-zA-Z0-9/_-]+)"',
        rf'"/{service}/\1"',
        content
    )
    
    return content