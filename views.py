from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re

@csrf_exempt
def proxy_view(request, service, path=''):
    url = f"https://{service}.up.railway.app/{path}"
    
    print(f"Proxying to: {url}")
    
    try:
        # Prepare cookies
        cookies = {}
        for key, value in request.COOKIES.items():
            cookies[key] = value
        
        resp = requests.request(
            method=request.method,
            url=url,
            headers={
                **{k: v for k, v in request.headers.items() 
                   if k.lower() not in ['connection', 'cookie', 'host']},
                'Host': f'{service}.up.railway.app',
                'X-Forwarded-Host': request.get_host(),
                'X-Forwarded-Proto': 'https' if request.is_secure() else 'http',
                'Referer': f'https://{service}.up.railway.app/{path}',
                'Origin': f'https://{service}.up.railway.app',
            },
            data=request.body,
            cookies=cookies,
            allow_redirects=False
        )
        
        content_type = resp.headers.get('content-type', '')
        
        # For HTML, rewrite paths
        if 'text/html' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            content = re.sub(r'(href|src|action)="(/[^"]*)"', rf'\1="/{service}\2"', content)
            content = re.sub(r"(href|src|action)='(/[^']*)'", rf"\1='/{service}\2'", content)
            response = HttpResponse(content, status=resp.status_code)
        else:
            response = HttpResponse(resp.content, status=resp.status_code)
        
        # Copy headers
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length', 'set-cookie']:
                if key.lower() == 'location':
                    if value.startswith('/'):
                        value = f'/{service}{value}'
                    elif value.startswith(f'https://{service}.up.railway.app/'):
                        value = value.replace(f'https://{service}.up.railway.app/', f'/{service}/')
                response[key] = value
        
        # Handle Set-Cookie separately to properly rewrite each cookie
        if 'Set-Cookie' in resp.headers:
            for cookie in resp.raw.headers.getlist('Set-Cookie'):
                # Remove domain restrictions so cookie works on proxy domain
                cookie = re.sub(r';\s*Domain=[^;]+', '', cookie, flags=re.IGNORECASE)
                # Change path to include service prefix
                cookie = re.sub(r'(Path=)(/[^;]*)', rf'\1/{service}\2', cookie, flags=re.IGNORECASE)
                response['Set-Cookie'] = cookie
        
        return response
        
    except Exception as e:
        print(f"Proxy error: {e}")
        return HttpResponse(f"Proxy error: {str(e)}", status=502)

def home(request):
    return HttpResponse("Proxy is running")