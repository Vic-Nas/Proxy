# Path-Based Reverse Proxy

Route multiple services through a single domain using URL paths instead of subdomains.

## Why?

✨ **One DNS record** - One domain, many services  
🚀 **Path routing** - `yourdomain.com/app/` instead of `app.yourdomain.com`  
🛡️ **Transparent** - JavaScript apps work without modification  

## Quick Start

```bash
# 1. Set environment
SERVICE_dev=vicnasdev.github.io
SERVICE_api=api.example.com
SECRET_KEY=your-secret-key
```

# 2. Deploy (Railway, Docker, VPS, etc.)
**Easiest:** [Deploy to Railway](https://railway.com?referralCode=ZIdvo-) (includes free credits)

# 3. Point DNS: yourdomain.com → your-proxy

**Usage:** `yourdomain.com/dev/` → `vicnasdev.github.io/`

## How It Works

The proxy rewrites content to be transparent:
- **JavaScript** - `window.location.pathname` sees clean paths (no `/service/` prefix)
- **Links/Assets** - Relative URLs get `/service/` prefix to route through proxy
- **API calls** - Absolute URLs left untouched

## Troubleshooting

- **Not working?** Hard refresh (Ctrl+Shift+R) to clear cache
- **Debugging?** Set `DEBUG=True` to disable caching and see detailed logs

## Contributing

Keep it **light**, **clear**, and **general**. PRs welcome!

**Live demo:** https://vicnas.me