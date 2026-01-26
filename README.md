# 🔄 Path-Based Reverse Proxy

A lightweight Django-based reverse proxy that routes requests through URL paths instead of subdomains. Perfect for consolidating multiple backend services under a single domain.

## What It Does

Instead of managing multiple subdomains:
- ❌ `https://api.yourdomain.com/users`
- ❌ `https://admin.yourdomain.com/dashboard`
- ❌ `https://web.yourdomain.com/home`

Access everything through paths:
- ✅ `https://yourdomain.com/api/users`
- ✅ `https://yourdomain.com/admin/dashboard`
- ✅ `https://yourdomain.com/web/home`

## How It Works

The proxy intercepts requests at `/{service}/{path}` and forwards them to your configured backend:

```
GET /api/users/123
  ↓
GET https://api.up.railway.app/users/123
  ↓
Response returned to client
```

It automatically rewrites:
- HTML links, images, and forms
- JavaScript fetch() calls
- Redirects and cookies
- Location headers

## Quick Start

### 1. Configure Your Backend Pattern

Edit `config.py`:

```python
# Change this to match your deployment platform
TARGET_DOMAIN_PATTERN = "{service}.up.railway.app"

# Examples for other platforms:
# TARGET_DOMAIN_PATTERN = "{service}.onrender.com"
# TARGET_DOMAIN_PATTERN = "{service}.fly.dev"
# TARGET_DOMAIN_PATTERN = "{service}.yourdomain.com"
```

### 2. Deploy

**Railway:**
```bash
railway up
```

**Docker:**
```bash
docker build -t reverse-proxy .
docker run -p 8000:8000 -e PORT=8000 reverse-proxy
```

**Local Development:**
```bash
pip install -r requirements.txt
gunicorn wsgi:application --bind 0.0.0.0:8000
```

### 3. Use It

Access your services:
- `http://localhost:8000/api/endpoint` → proxies to `https://api.up.railway.app/endpoint`
- `http://localhost:8000/web/page` → proxies to `https://web.up.railway.app/page`

## Configuration

### Environment Variables

```bash
SECRET_KEY=your-secret-key-here
DEBUG=false
ALLOWED_HOSTS=yourdomain.com,*.yourdomain.com
PORT=8000  # For Railway/Render
```

### Security Options

In `config.py`:

```python
# Only allow specific services
ALLOWED_SERVICES = ['api', 'web', 'admin']

# Block certain service names
BLOCKED_SERVICES = ['www', 'mail', 'ftp', 'ssh']
```

## Use Cases

✅ **Perfect For:**
- Avoiding subdomain management complexity
- Single SSL certificate for all services
- Simplified DNS configuration
- Microservices behind one domain
- Development/staging environments

❌ **Not Ideal For:**
- High-traffic production (consider a proper API gateway)
- Services requiring WebSocket persistence
- Very large file uploads/downloads

## How URLs Are Rewritten

**HTML:**
```html
<!-- Original from backend -->
<a href="/login">Login</a>
<img src="/static/logo.png">

<!-- Rewritten by proxy -->
<a href="/api/login">Login</a>
<img src="/api/static/logo.png">
```

**JavaScript:**
```javascript
// Original
fetch('/api/data')

// Rewritten
fetch('/api/api/data')
```

**Redirects:**
```
Location: /dashboard
  ↓
Location: /admin/dashboard
```

## Architecture

```
Client Request
    ↓
Your Domain (this proxy)
    ↓
/{service}/{path}
    ↓
Forwarded to: https://{service}.platform.com/{path}
    ↓
Response rewritten
    ↓
Returned to Client
```

## Files Overview

- `config.py` - Main configuration (edit this!)
- `views.py` - Request handling and URL rewriting
- `urls.py` - URL routing
- `settings.py` - Django settings
- `wsgi.py` - WSGI application entry point
- `Dockerfile` - Container configuration

## Troubleshooting

**Service returns 404:**
- Check `TARGET_DOMAIN_PATTERN` is correct
- Verify the backend service is actually running
- Check service name doesn't contain dots or special chars

**JavaScript/CSS not loading:**
- Ensure paths in your backend start with `/`
- Check browser console for 404s
- May need custom rewriting for specific frameworks

**Cookies not working:**
- Check `SameSite` and `Secure` flags
- Ensure proxy and backend use same protocol (HTTP/HTTPS)

## Contributing

This is designed to be simple and hackable. Feel free to:
- Add support for WebSockets
- Implement caching layers
- Add authentication middleware
- Customize URL rewriting patterns

## License

MIT - Use however you want!

## Credits

A simple tool for those who don't like adding subdomains. 🚀