"""URL rewriting logic for proxy."""
import re
from utils.logging import log


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
    
    # FIX: Changed [^"\'`]* to [^"\'`>]* to prevent matching across tags
    content = re.sub(
        r'((?:href|src|action)=)(["\'`])(/(?!/)[^"\'`>]*)\2',
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