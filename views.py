from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests

@csrf_exempt
def proxy_view(request, service, path=''):
    # Build target URL
    url = f"https://{service}.up.railway.app/{path}"
    
    # Forward request
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() 
                    if k.lower() not in ['host', 'connection']},
            data=request.body,
            cookies=request.COOKIES,
            allow_redirects=False,
            stream=True
        )
        
        # Build response
        response = StreamingHttpResponse(
            resp.iter_content(chunk_size=8192),
            status=resp.status_code
        )
        
        # Copy headers
        for key, value in resp.headers.items():
            if key.lower() not in ['connection', 'transfer-encoding']:
                if key.lower() == 'location':
                    # Rewrite redirects
                    if value.startswith('/'):
                        value = f'/{service}{value}'
                    elif value.startswith(f'https://{service}.up.railway.app'):
                        value = value.replace(f'https://{service}.up.railway.app', f'/{service}')
                response[key] = value
        
        return response
        
    except requests.RequestException as e:
        return HttpResponse(f"Proxy error: {str(e)}", status=502)

def home(request):
    return HttpResponse("Proxy is running")