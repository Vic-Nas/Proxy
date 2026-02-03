"""Proxy request handling."""
import os
import requests
import re
from django.http import HttpResponse
from config import DEBUG
from utils.logging import log, LOG_LEVEL
from utils.templates import error_page, path_not_found
from utils.rewrite import rewrite_content


def build_target_url(target_domain, base_path, path, query_string):
    """Build the target URL for the backend service."""
    url = f"https://{target_domain}{base_path}/{path}"
    if query_string:
        url += f"?{query_string}"
    return url


def prepare_headers(request, service, target_domain):
    """Prepare headers for backend request."""
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
    
    return headers


def should_log_request(path):
    """
    Determine if this request should be logged.

    LOG_LEVEL=debug  → log everything (same as DEBUG=True)
    LOG_LEVEL=info   → skip static asset requests
    LOG_LEVEL=error  → skip everything (errors still logged via log())
    
    Falls back to the DEBUG flag when LOG_LEVEL is not set explicitly,
    preserving existing behaviour.
    """
    # debug level: log all requests
    if LOG_LEVEL == 'debug' or DEBUG:
        return True

    # error level: silence all non-error traffic
    if LOG_LEVEL == 'error':
        return False

    # info level: skip known static asset extensions
    asset_extensions = ['.svg', '.ico', '.css', '.js', '.png', '.jpg', '.woff', '.woff2', '.ttf']
    return not any(path.endswith(ext) for ext in asset_extensions)


def is_asset_path(path):
    """Check if the path is a static asset."""
    asset_extensions = ['.js', '.css', '.svg', '.ico', '.png', '.jpg', '.jpeg', '.gif', 
                       '.woff', '.woff2', '.ttf', '.eot', '.otf', '.webp']
    return any(path.endswith(ext) for ext in asset_extensions)


def handle_404_response(resp, path, service, target_domain):
    """Handle 404 responses from backend."""
    # For assets, pass through the 404 without our error page
    if is_asset_path(path):
        return HttpResponse(resp.content, status=404, content_type=resp.headers.get('content-type', 'text/plain'))
    # For HTML pages, show path not found
    return path_not_found(service, path, target_domain)


def process_response_content(content, content_type, service, target_domain, url):
    """Process response content (rewrite URLs if text)."""
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
        
        return text_content, True
    
    return content, False


def copy_response_headers(resp, response, service, target_domain):
    """Copy headers from backend response to our response."""
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


def apply_cache_headers(response):
    """Apply cache busting headers in DEBUG mode."""
    if DEBUG:
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Surrogate-Control'] = 'no-store'
        response['Vary'] = '*'


def handle_set_cookies(resp, response):
    """Handle Set-Cookie headers from backend."""
    if 'Set-Cookie' in resp.headers:
        for cookie in resp.raw.headers.getlist('Set-Cookie'):
            response['Set-Cookie'] = cookie


def make_proxy_request(service, target_domain, base_path, path, request, url):
    """Make request to backend service."""
    headers = prepare_headers(request, service, target_domain)
    cookies = {key: value for key, value in request.COOKIES.items()}
    
    if should_log_request(path):
        log(f"[PROXY] {request.method} /{service}/{path} → {url}")
    
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
    
    return resp