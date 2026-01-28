# Path-Based Reverse Proxy

Route multiple services through a single domain using URL paths instead of subdomains.

## Why?

✨ **One DNS record** - One domain, many services  
🚀 **Path routing** - `yourdomain.com/app/` instead of `app.yourdomain.com`  
🛡️ **Transparent** - JavaScript apps work without modification  
🎨 **Clean error pages** - Friendly 404s with optional coffee button

## Quick Start

```bash
# 1. Set environment variables
SECRET_KEY=your-secret-key # Random long string to secure the app
SERVICE_dev=vicnasdev.github.io
SERVICE_api=api.example.com
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
- **Base tags** - Automatically rewritten to include service prefix

### Debug Mode
Set `DEBUG=true` to:
- Disable caching for easier testing
- See detailed rewrite logs
- Get more verbose error messages

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_*` | - | Service mappings (e.g., `SERVICE_dev=example.com`) |
| `SECRET_KEY` | `change-me-in-production` | Django secret key |
| `DEBUG` | `false` | Enable debug mode (disables caching) |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed hosts |
| `COFFEE_USERNAME` | `vicnas` | Buy Me a Coffee username |
| `COFFEE` | `true` | Show coffee button on error pages |

## Troubleshooting

- **Debugging?** Set `DEBUG=true` to disable caching and see detailed logs
- **Still broken?** Check the logs for `[REWRITE]` messages to see what's being changed

## Contributing

Keep it **light**, **clear**, and **general**. PRs welcome!
But as this can be easily broken, Issues are better.

**Live demo:** https://vicnas.me