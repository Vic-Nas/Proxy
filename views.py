from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import re

@csrf_exempt
def proxy_view(request, service, path=''):
    url = f"https://{service}.up.railway.app/{path}"
    
    print(f"Proxying to: {url}")
    
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={
                **{k: v for k, v in request.headers.items() 
                   if k.lower() not in ['connection']},
                'Host': f'{service}.up.railway.app',
                'X-Forwarded-Host': request.get_host(),
                'X-Forwarded-Proto': 'https' if request.is_secure() else 'http',
            },
            data=request.body,
            cookies=request.COOKIES,
            allow_redirects=False
        )
        
        content_type = resp.headers.get('content-type', '')
        
        # For HTML, rewrite paths
        if 'text/html' in content_type:
            content = resp.content.decode('utf-8', errors='ignore')
            
            # Rewrite absolute paths to include service prefix
            # /static/ -> /service/static/
            # /api/ -> /service/api/
            # href="/" -> href="/service/"
            content = re.sub(r'(href|src|action)="(/[^"]*)"', rf'\1="/{service}\2"', content)
            content = re.sub(r"(href|src|action)='(/[^']*)'", rf"\1='/{service}\2'", content)
            
            response = HttpResponse(content, status=resp.status_code)
        else:
            # For non-HTML (CSS, JS, images), stream as-is
            response = HttpResponse(resp.content, status=resp.status_code)
        
        # Copy headers
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length']:
                if key.lower() == 'location':
                    # Rewrite redirects
                    if value.startswith('/'):
                        value = f'/{service}{value}'
                    elif value.startswith(f'https://{service}.up.railway.app/'):
                        value = value.replace(f'https://{service}.up.railway.app/', f'/{service}/')
                response[key] = value
        
        return response
        
    except Exception as e:
        print(f"Proxy error: {e}")
        return HttpResponse(f"Proxy error: {str(e)}", status=502)

def home(request):
    return HttpResponse("Proxy is running")