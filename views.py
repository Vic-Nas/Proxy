from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
import requests
import re
import sys
import os
from collections import deque
from config import SERVICES, BLOCKED_SERVICES, DEBUG, COFFEE_USERNAME, SHOW_COFFEE, ENABLE_LOGS, SHOW_FIXES

# Import version info
try:
    from version import __name__ as app_name
except ImportError:
    app_name = "Flashy"

# Get version from git tags
def get_version():
    """Get version from git tags, fallback to version.py or 'dev'."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip('v')
    except:
        pass
    
    # Fallback to version.py
    try:
        from version import __version__
        return __version__
    except:
        pass
    
    return "1.0.0"

__version__ = get_version()

# DEBUG mode does aggressive cache busting:
# - Strips ALL cache headers (ETag, Cache-Control, Expires, Last-Modified, Age, Vary)
# - Adds multiple no-cache directives (Cache-Control, Pragma, Expires, Surrogate-Control)
# - Logs EVERY request including assets
# - Forces browser/proxy revalidation on every request

# Simple in-memory log storage (last 1000 lines)
LOG_BUFFER = deque(maxlen=1000)


def log(msg):
    """Log to stdout immediately and optionally store in buffer."""
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()
    
    # Store in buffer if logs service is enabled
    if ENABLE_LOGS:
        from datetime import datetime
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        LOG_BUFFER.append(f"[{timestamp}] {msg}")


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


def path_not_found(service, path, target_domain):
    """Show 404 page when service exists but path doesn't."""
    html = render_template('error.html', {
        'title': '404 - Path Not Found',
        'message': f'The service "{service}" exists, but this path was not found on the backend.',
        'error_type': 'HTTP 404 Not Found',
        'service': service,
        'target': target_domain,
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
    
    # Get latest changelog if FIXES=true
    # Get latest changelog if FIXES=true
    latest_fixes = None
    if SHOW_FIXES:
        try:
            changelog_path = os.path.join(os.path.dirname(__file__), 'CHANGELOG.md')
            with open(changelog_path, 'r') as f:
                latest_fixes = f.read()
        except:
            pass
    
    html = render_template('home.html', {
        'services': SERVICES,
        'version': __version__,
        'app_name': app_name,
        'show_fixes': SHOW_FIXES,
        'latest_fixes': latest_fixes,
        'show_coffee': SHOW_COFFEE,
        'coffee_username': COFFEE_USERNAME,
    })
    return HttpResponse(html)


def logs_view(request):
    """Show recent logs if LOGS=true."""
    if not ENABLE_LOGS:
        return HttpResponse("Logs service not enabled. Set LOGS=true to enable.", status=404)
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proxy Logs</title>
  <style>
    body {
      font-family: 'Courier New', monospace;
      background: #1e1e1e;
      color: #d4d4d4;
      margin: 0;
      padding: 20px;
    }
    h1 {
      color: #4ec9b0;
      font-size: 1.5em;
    }
    .log-container {
      background: #252526;
      padding: 20px;
      border-radius: 8px;
      overflow-x: auto;
    }
    .log-line {
      padding: 4px 0;
      border-bottom: 1px solid #333;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
    .log-line:hover {
      background: #2d2d30;
    }
    .timestamp {
      color: #858585;
    }
    .proxy { color: #4ec9b0; }
    .rewrite { color: #dcdcaa; }
    .error { color: #f48771; }
    .warning { color: #ce9178; }
    .refresh {
      display: inline-block;
      margin: 10px 0;
      padding: 8px 16px;
      background: #0e639c;
      color: white;
      text-decoration: none;
      border-radius: 4px;
    }
    .refresh:hover {
      background: #1177bb;
    }
  </style>
</head>
<body>
  <h1>📋 Proxy Logs (Last 1000 lines)</h1>
  <a href="/_logs/" class="refresh">🔄 Refresh</a>
  <a href="/" class="refresh">← Home</a>
  <div class="log-container">
"""
    
    if not LOG_BUFFER:
        html += '<div class="log-line">No logs yet...</div>'
    else:
        for line in LOG_BUFFER:
            css_class = ""
            if "[PROXY]" in line:
                css_class = "proxy"
            elif "[REWRITE]" in line:
                css_class = "rewrite"
            elif "[ERROR]" in line:
                css_class = "error"
            elif "[WARNING]" in line:
                css_class = "warning"
            
            html += f'<div class="log-line {css_class}">{line}</div>\n'
    
    html += """
  </div>
</body>
</html>
"""
    
    return HttpResponse(html)


@csrf_exempt
def proxy_view(request, service, path=''):
    """Main proxy logic - forwards requests to backend services."""
    
    # Handle internal logs service
    if service == '_logs' and ENABLE_LOGS:
        return logs_view(request)
    
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
    
    # In DEBUG mode, log ALL requests. Otherwise skip assets to reduce noise
    if DEBUG:
        log(f"[PROXY] {request.method} /{service}/{path} → {url}")
    elif not any(path.endswith(ext) for ext in ['.svg', '.ico', '.css', '.js', '.png', '.jpg', '.woff', '.woff2', '.ttf']):
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
            # For assets (.js, .css, images, etc.), pass through the 404 without our error page
            # This prevents MIME type errors when browsers try to execute our HTML as JS/CSS
            if any(path.endswith(ext) for ext in ['.js', '.css', '.svg', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.woff', '.woff2', '.ttf', '.eot', '.otf', '.webp']):
                return HttpResponse(resp.content, status=404, content_type=resp.headers.get('content-type', 'text/plain'))
            # For HTML pages, show path not found (service exists, but this path doesn't)
            return path_not_found(service, path, target_domain)
        
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
                # Strip ALL caching headers in DEBUG mode
                elif DEBUG and key.lower() in ['etag', 'cache-control', 'expires', 'last-modified', 'age', 'vary']:
                    continue
                response[key] = value
        
        # Super aggressive cache busting in DEBUG mode
        if DEBUG:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            # Prevent all forms of caching
            response['Surrogate-Control'] = 'no-store'
            # Force revalidation
            response['Vary'] = '*'
        
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
        return bool(re.match(r'^https?://', url)) or '//' in url or url.startswith('data:')
    
    # Rewrite helper: add /service/ prefix to relative URLs
    def rewrite_url(match):
        attr = match.group(1)
        quote = match.group(2)
        url = match.group(3)
        
        # Skip if already has service prefix
        if url.startswith(f'/{service}/'):
            return match.group(0)
        
        # Skip absolute URLs (http://, https://, //, data:)
        if is_absolute(url):
            return match.group(0)
        
        # Add service prefix to relative URLs
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
