from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
import requests
import re
import sys
from config import SERVICES, BLOCKED_SERVICES, DEBUG, COFFEE_USERNAME, SHOW_COFFEE


def log(msg):
    """Log to stdout immediately."""
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()


def render_template(template_name, context):
    """Simple template rendering."""
    template = loader.get_template(template_name)
    return template.render(context)


def service_not_found(service, reason=None):
    """Show friendly 404 page when service doesn't exist."""
    html = render_template('404.html', {
        'service': service,
        'reason': reason,
        'show_coffee': SHOW_COFFEE,
        'coffee_username': COFFEE_USERNAME,
    })
    return HttpResponse(html, status=404)


def error_page(title, message, error_type, service=None, target=None, status=502):
    """Show error page for backend issues."""
    html = render_template('error.html', {
        'title': title,
        'message': message,
        'error_type': error_type,
        'service': service,
        'target': target,
        'show_coffee': SHOW_COFFEE,
        'coffee_username': COFFEE_USERNAME,
    })
    return HttpResponse(html, status=status)


def home(request):
    """Show available services on homepage."""
    html = render_template('home.html', {'services': SERVICES})
    return HttpResponse(html)


@csrf_exempt
def proxy_view(request, service, path=''):
    """Main proxy logic - forwards requests to backend services."""
    
    # Block reserved service names
    if service in BLOCKED_SERVICES:
        return JsonResponse({'error': 'Blocked'}, status=403)
    
    # Only allow explicitly defined services
    if service not in SERVICES:
        return service_not_found(service, "Service not configured")
    
    target_domain = SERVICES[service]
    
    # Ensure trailing slash for service root
    if not path or path == '/':
        if not request.path.endswith('/'):
            return HttpResponseRedirect(f'/{service}/')
        path = ''
    
    # Build target URL
    url = f"https://{target_domain}/{path}"
    if request.META.get('QUERY_STRING'):
        url += f"?{request.META['QUERY_STRING']}"
    
    # Log main requests (skip assets)
    if not any(path.endswith(ext) for ext in ['.svg', '.ico', '.css', '.js', '.png', '.jpg', '.woff', '.woff2', '.ttf']):
        log(f"[PROXY] {request.method} /{service}/{path} → {url}")
    
    try:
        # Prepare headers
        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ['connection', 'host', 'accept-encoding']:
                headers[k] = v
        
        # Rewrite referer and origin to match target
        if 'Referer' in headers:
            headers['Referer'] = re.sub(rf'https?://[^/]+/{service}/', f'https://{target_domain}/', headers['Referer'])
        if 'Origin' in headers:
            headers['Origin'] = f'https://{target_domain}'
        
        headers['Host'] = target_domain
        headers['X-Forwarded-Host'] = request.get_host()
        headers['X-Forwarded-Proto'] = 'https' if request.is_secure() else 'http'
        
        cookies = {key: value for key, value in request.COOKIES.items()}
        
        # Make request to backend
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.body,
            cookies=cookies,
            allow_redirects=False,
            timeout=30
        )
        
        # Handle 404s from backend
        if resp.status_code == 404:
            return service_not_found(service, f"Backend returned 404 for: /{path}")
        
        # Get content (no decompression needed - requests handles it)
        content = resp.content
        content_type = resp.headers.get('content-type', '')
        
        # Rewrite text content (HTML, JS, JSON, CSS)
        is_text = any(x in content_type.lower() for x in ['text/', 'javascript', 'json'])
        
        if is_text:
            log(f"[REWRITE] Processing {url}")
            log(f"[REWRITE]   Content-Type: {content_type}")
            
            text_content = content.decode('utf-8', errors='ignore')
            original_len = len(text_content)
            
            # Track what we're rewriting
            has_pathname = 'window.location.pathname' in text_content or 'location.pathname' in text_content
            has_api = 'api.github.com' in text_content or 'api.' in text_content
            
            log(f"[REWRITE]   Contains pathname reads: {has_pathname}")
            log(f"[REWRITE]   Contains API calls: {has_api}")
            
            text_content = rewrite_content(text_content, service, target_domain)
            
            if len(text_content) != original_len:
                log(f"[REWRITE]   ✓ Modified ({original_len} → {len(text_content)} bytes)")
            else:
                log(f"[REWRITE]   No changes made")
            
            response = HttpResponse(text_content, status=resp.status_code)
        else:
            response = HttpResponse(content, status=resp.status_code)
        
        # Copy headers from backend response
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    # Rewrite redirects to include service prefix
                    if f'/{service}/' not in value and f'/{service}' not in value:
                        if value.startswith(f'https://{target_domain}'):
                            path = value[len(f'https://{target_domain}'):]
                            value = f'/{service}{path or "/"}'
                        elif value.startswith('/'):
                            value = f'/{service}{value}'
                # Strip caching headers in DEBUG mode for easier testing
                elif DEBUG and key.lower() in ['etag', 'cache-control', 'expires', 'last-modified']:
                    continue
                response[key] = value
        
        # Add no-cache headers in DEBUG mode
        if DEBUG:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
        
        # Handle cookies
        if 'Set-Cookie' in resp.headers:
            for cookie in resp.raw.headers.getlist('Set-Cookie'):
                response['Set-Cookie'] = cookie
        
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


def rewrite_content(content, service, target_domain):
    """
    Rewrite URLs in HTML/JS/CSS to work behind the proxy.
    
    Key rewrites:
    1. window.location.pathname → strips /service/ prefix so apps see clean paths
    2. Relative URLs (/path) → adds /service/ prefix so they route through proxy
    3. Base tag → adds /service/ prefix to base href
    """
    
    # Rewrite pathname reads to hide the /service/ prefix from JavaScript
    # This makes the proxy transparent - apps don't know they're behind a proxy
    pathname_count = content.count('window.location.pathname') + content.count('location.pathname')
    if pathname_count > 0:
        log(f"[REWRITE]   Found {pathname_count} pathname references, rewriting...")
    
    # Match window.location.pathname (but not document.location.pathname)
    content = re.sub(
        r'(?<!document\.)window\.location\.pathname\b',
        f'(window.location.pathname.replace(/^\\/{service}\\//, "/"))',
        content
    )
    # Match standalone location.pathname (but not window.location or document.location)
    content = re.sub(
        r'(?<!window\.)(?<!document\.)location\.pathname\b',
        f'(location.pathname.replace(/^\\/{service}\\//, "/"))',
        content
    )
    
    # Rewrite <base> tag if present
    content = re.sub(
        r'<base\s+href="/"',
        f'<base href="/{service}/"',
        content,
        flags=re.IGNORECASE
    )
    
    # Helper: check if URL is absolute (don't rewrite those)
    def is_absolute(url):
        return bool(re.match(r'^https?://', url)) or '//' in url
    
    # Helper: check if we should skip rewriting this URL
    def should_skip(match, url):
        # Skip absolute URLs
        if is_absolute(url):
            return True
        
        # Check surrounding context for API calls or external references
        start = max(0, match.start() - 30)
        end = min(len(content), match.end() + 30)
        context = content[start:end]
        
        # Skip if it looks like an API call or external URL reference
        skip_patterns = ['api.', '://', '.com/', '.io/', '.org/', '.net/', 'http']
        return any(pattern in context for pattern in skip_patterns)
    
    # Rewrite helper: add /service/ prefix to relative URLs
    def rewrite_url(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        
        # Skip if already has service prefix
        if url.startswith(f'/{service}/'):
            return match.group(0)
        
        # Skip if should not be rewritten
        if should_skip(match, url):
            return match.group(0)
        
        # Add service prefix
        return f'{attr}{quote}/{service}{url}{quote}'
    
    # Rewrite href/src/action attributes (only relative URLs starting with /)
    content = re.sub(
        r'((?:href|src|action)=)(["\'`])(/(?!/).[^"\'`]*)\2',
        rewrite_url,
        content
    )
    
    # Rewrite fetch() and similar API calls (only relative URLs)
    content = re.sub(
        r'(fetch\s*\(\s*)(["\'`])(/(?!/).[^"\'`]*)\2',
        rewrite_url,
        content
    )
    
    # Rewrite location assignments like location.href = "/path"
    content = re.sub(
        r'(location\.href\s*=\s*)(["\'`])(/(?!/).[^"\'`]*)\2',
        rewrite_url,
        content
    )
    
    return content