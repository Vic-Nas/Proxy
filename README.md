![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Django](https://img.shields.io/badge/django-5.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

# Flashy ⚡

Path-based reverse proxy - route multiple services through one domain.

## Quick Start

### Railway (Recommended)

Set environment variables and deploy:
```bash
SECRET_KEY=your-secret-key
SERVICE_dev=vicnasdev.github.io
SERVICE_api=api.example.com
```

[Fork and Deploy to Railway](https://railway.com?referralCode=ZIdvo-) (free credits included)

### Self-Hosted Docker

```bash
docker run -e SECRET_KEY=your-secret-key \
  -e SERVICE_dev=vicnasdev.github.io \
  -p 8000:8000 ghcr.io/vicnasdev/flashy
```

**Usage:** `yourdomain.com/dev/` → `vicnasdev.github.io/`

## How It Works

The proxy rewrites URLs so JavaScript apps work transparently:
- Pathname reads see clean paths (no `/service/` prefix)
- Relative URLs get `/service/` prefix automatically
- Absolute URLs (APIs, CDNs) stay untouched

## Comparison with Other Solutions

| Feature | Flashy | Nginx | Caddy | Cloudflare |
|---------|--------|-------|-------|-----------|
| **Setup Complexity** | 🟢 2 min | 🟠 30 min | 🟢 10 min | 🟠 15 min |
| **URL Rewriting** | 🟢 Automatic | 🔴 Manual regex | 🟠 Manual | 🟠 Limited |
| **JavaScript Apps** | 🟢 Transparent | 🔴 Breaks paths | 🔴 Breaks paths | 🟡 Partial |
| **Deploy Cost** | 🟢 Free (Railway) | 🟠 $5+/mo | 🟠 $5+/mo | 🟠 $20+/mo |
| **Configuration** | 🟢 Env vars | 🔴 Complex .conf | 🟢 Simple | 🟠 UI-based |
| **Self-Hosted** | 🟢 Easy (Docker) | 🟢 Yes | 🟢 Yes | 🔴 No |
| **Dynamic Services** | 🟢 Add anytime | 🔴 Restart needed | 🟡 Reload | 🟢 Dynamic |


## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_*` | - | Service mappings (e.g., `SERVICE_dev=example.com/path` or just create template `dev.html`) |
| `SERVICE_*_DESC` | _(optional)_ | Description for a service (e.g., `SERVICE_dev_DESC=Development site`) |
| `SERVICE_*_RANK` | `999` | Optional rank for ordering services (e.g., `SERVICE_api_RANK=1`) |
| `SERVICE_*_HIDE` | `false` | Optional per-service hide flag. Set `SERVICE_<name>_HIDE=true` to hide that service from the homepage (local templates respect this flag). |
| `SECRET_KEY` | `change-me-in-production` | Django secret key |
| `DEBUG` | `false` | Verbose logs, no caching |
| `LOG_LEVEL` | `info` | Log verbosity: `error` (errors only), `info` (summaries), `debug` (full rewrite detail) |
| `COFFEE` | `true` | Show coffee button on errors |
| `COFFEE_USERNAME` | `vicnas` | Coffee button username |

## Contributing

Keep it **light**, **clear**, and **general**. PRs welcome!

```bash
# Run tests before submitting
python test.py
```

See [VERSIONING.md](VERSIONING.md) for releases.

**Live demo:** https://vicnas.me