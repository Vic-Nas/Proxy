# 🔄 Path-Based Reverse Proxy with WebSocket Support

A Django-based reverse proxy that routes requests through URL paths instead of subdomains. **Now with full WebSocket support!**

## ⚡ New in v2.1: WebSocket Support

Your proxy now handles WebSocket connections using Django Channels! This fixes errors like:
```
Not Found: /ws/match/174/
```

## What It Does

Routes all traffic (HTTP + WebSocket) through path-based URLs:

**HTTP:**
- `https://yourdomain.com/api/users` → `https://api.up.railway.app/users`

**WebSockets:**
- `wss://yourdomain.com/dash0/ws/match/174/` → `wss://dash0.up.railway.app/ws/match/174/`

## Quick Start

### 1. Deploy Updated Version

```bash
# Replace ALL your files with these updated ones
git add .
git commit -m "Add WebSocket support via Django Channels"
git push
```

### 2. Railway Will Auto-Deploy

Railway will detect the changes and redeploy. The new version uses **Daphne** (ASGI server) instead of Gunicorn to support WebSockets.

### 3. Test WebSocket Connection

Open your browser console on `https://vicnas.me/dash0/` and check if WebSocket connects successfully.

## What Changed

### Before (Gunicorn - HTTP only):
```dockerfile
CMD gunicorn wsgi:application
```
❌ Could not handle WebSocket connections
❌ Got "Not Found" errors for `/ws/` paths

### After (Daphne - HTTP + WebSocket):
```dockerfile
CMD daphne routing:application
```
✅ Handles both HTTP and WebSocket
✅ Proxies WebSocket connections to backend

## Architecture

```
Client
  ↓
HTTPS/WSS: vicnas.me
  ↓
Django Channels (Daphne ASGI Server)
  ├─ HTTP requests → views.py (existing proxy logic)
  └─ WebSocket → consumers.py (new WebSocket proxy)
        ↓
  Backend: dash0.up.railway.app/ws/...
```

## Files Overview

**New Files:**
- `routing.py` - ASGI routing configuration (HTTP + WebSocket)
- `consumers.py` - WebSocket proxy consumer

**Updated Files:**
- `requirements.txt` - Added `channels[daphne]` and `websockets`
- `settings.py` - Added Channels configuration
- `Dockerfile` - Changed from Gunicorn to Daphne
- `views.py` - Improved WebSocket URL rewriting

## Troubleshooting Your Specific Errors

### Issue: "Not Found: /ws/match/174/"

**Problem:** WebSocket URL not being rewritten correctly

**Solution:** This update fixes WebSocket URL rewriting. The proxy now correctly converts:
- `/ws/match/174/` → `/dash0/ws/match/174/`

### Issue: "Not Found: /matches/multiplayer/"

**Problem:** Frontend JavaScript creating URLs without service prefix

**Root Cause:** Your backend's JavaScript is likely doing something like:
```javascript
// This bypasses the proxy's URL rewriting
window.location = '/matches/multiplayer/';
```

**Solutions:**

1. **Check your backend's JavaScript redirect logic**
   - Look for `window.location =`, `window.location.href =`
   - These should use relative URLs that get rewritten

2. **If using a JavaScript framework router (React/Vue):**
   ```javascript
   // Bad: Hardcoded paths
   router.push('/matches/multiplayer')
   
   // Good: Use basename/base path
   const router = createRouter({
     basename: '/dash0',  // or detect from window.location
   })
   ```

3. **Quick backend fix - make it prefix-aware:**
   ```javascript
   // Add this to your backend's main.js
   const BASE_PATH = '/' + window.location.pathname.split('/')[1];
   
   // Then use it everywhere:
   window.location.href = BASE_PATH + '/matches/multiplayer/';
   fetch(BASE_PATH + '/api/endpoint');
   ```

## Testing

### Test WebSocket in Browser Console:
```javascript
const ws = new WebSocket('/dash0/ws/match/174/');
ws.onopen = () => console.log('✅ WebSocket connected!');
ws.onerror = (e) => console.error('❌ WebSocket error:', e);
```

### Expected Railway Logs:
```
[WS PROXY] Connecting to wss://dash0.up.railway.app/ws/match/174/
```

## Configuration

Edit `config.py`:
```python
TARGET_DOMAIN_PATTERN = "{service}.up.railway.app"
ALLOWED_SERVICES = []  # Leave empty to allow all
BLOCKED_SERVICES = ['www', 'mail']
```

## Security Features

- ✅ HTTPS enforcement
- ✅ Secure WebSocket (wss://) upgrade
- ✅ Mixed content prevention
- ✅ Secure cookie flags
- ✅ Content Security Policy

## License

MIT

## Changelog

### v2.1 - WebSocket Support
- Django Channels + Daphne for WebSocket
- Fixes "Not Found: /ws/..." errors
- Improved URL rewriting

### v2.0 - HTTPS Enforcement
- Mixed content prevention
- Secure cookies