from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import requests
import re
import gzip
import zlib
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
    <li>Environment variable <code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">SERVICE_{service}=your-domain.com</code> is defined</li>
    <li>The target service is currently running and accessible</li>
    <li>The domain in SERVICE_{service} is correct</li>
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
    
    # Only log HTML/API requests, not assets
    if not any(path.endswith(ext) for ext in ['.svg', '.ico', '.css', '.js', '.png', '.jpg', '.woff', '.woff2', '.ttf']):
        print(f"[PROXY] {request.method} /{service}/{path} → {url}")
    
    try:
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ['connection', 'host']:
                headers[k] = v
        
        # Remove accept-encoding to prevent compression
        if 'Accept-Encoding' in headers:
            del headers['Accept-Encoding']
        
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
        
        # Manually handle decompression
        content = resp.content
        encoding = resp.headers.get('content-encoding', '').lower()
        
        if encoding == 'gzip':
            try:
                content = gzip.decompress(content)
            except Exception as e:
                print(f"[WARNING] Gzip decompression failed: {e}")
        elif encoding == 'deflate':
            try:
                content = zlib.decompress(content)
            except Exception as e:
                print(f"[WARNING] Deflate decompression failed: {e}")
        
        content_type = resp.headers.get('content-type', '')
        
        # Rewrite HTML and JS/JSON
        is_text = any(x in content_type.lower() for x in ['text/', 'javascript', 'json'])
        
        if is_text:
            print(f"[REWRITE] Processing {url}")
            print(f"[REWRITE]   Content-Type: {content_type}")
            
            text_content = content.decode('utf-8', errors='ignore')
            original_len = len(text_content)
            
            # Check what we're about to rewrite
            has_pathname = 'window.location.pathname' in text_content or 'location.pathname' in text_content
            has_api = 'api.github.com' in text_content or 'api.' in text_content
            
            print(f"[REWRITE]   Contains pathname reads: {has_pathname}")
            print(f"[REWRITE]   Contains API calls: {has_api}")
            
            text_content = rewrite_content(text_content, service)
            
            if len(text_content) != original_len:
                print(f"[REWRITE]   ✓ Modified ({original_len} → {len(text_content)} bytes)")
            else:
                print(f"[REWRITE]   No changes made")
            
            response = HttpResponse(text_content, status=resp.status_code)
        elif 'javascript' in content_type or 'application/json' in content_type:
            text_content = content.decode('utf-8', errors='ignore')
            # Don't rewrite JS/JSON if it contains external API calls
            if 'api.' not in text_content and '://api' not in text_content:
                text_content = rewrite_content(text_content, service)
            response = HttpResponse(text_content, status=resp.status_code)
        else:
            response = HttpResponse(content, status=resp.status_code)
        
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    # Skip if already contains service prefix
                    if f'/{service}/' in value or f'/{service}' in value:
                        pass
                    # If it's an absolute URL to the target domain, convert to service path
                    elif value.startswith(f'https://{target_domain}'):
                        path = value[len(f'https://{target_domain}'):]
                        value = f'/{service}{path or "/"}'
                    # If it's a relative path, add service prefix
                    elif value.startswith('/'):
                        value = f'/{service}{value}'
                # Remove cache headers for text content so it always gets rewritten
                elif key.lower() in ['etag', 'cache-control', 'expires', 'last-modified'] and is_text:
                    continue
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
    """Rewrite relative URLs and pathname reads to work behind proxy."""
    
    # ALWAYS rewrite pathname reads (this doesn't touch API URLs)
    pathname_count = content.count('window.location.pathname') + content.count('location.pathname')
    if pathname_count > 0:
        print(f"[REWRITE]   Found {pathname_count} pathname references, rewriting...")
    
    content = re.sub(
        r'\bwindow\.location\.pathname\b',
        f'(window.location.pathname.replace(/^\\/{service}\\//, "/"))',
        content
    )
    content = re.sub(
        r'\blocation\.pathname\b',
        f'(location.pathname.replace(/^\\/{service}\\//, "/"))',
        content
    )
    
    def is_safe(match):
        """Check if match is inside an absolute URL."""
        start = max(0, match.start() - 20)
        end = min(len(content), match.end() + 20)
        context = content[start:end]
        return not any(x in context for x in ['://', '.com', '.io', '.org', '.net', 'api.'])
    
    def rewrite(match, quote='"'):
        return match.group(1) + quote + f'/{service}' + match.group(2) + quote if is_safe(match) else match.group(0)
    
    # Rewrite href/src/action attributes (but not if they're absolute URLs)
    content = re.sub(r'((?:href|src|action)=")(/[a-zA-Z][^"]*)"', lambda m: rewrite(m, '"'), content)
    content = re.sub(r"((?:href|src|action)=')(/[a-zA-Z][^']*)'", lambda m: rewrite(m, "'"), content)
    
    # Rewrite fetch calls (but not if they're absolute URLs)
    content = re.sub(r'(fetch\s*\(\s*")(/[a-zA-Z][^"]*)"', lambda m: rewrite(m, '"'), content)
    
    return content