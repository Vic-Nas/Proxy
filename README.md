![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Django](https://img.shields.io/badge/django-5.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

# Flashy ⚡

Path-based reverse proxy - route multiple services through one domain.

## Quick Start

```bash
# 1. Set your services
SERVICE_dev=vicnasdev.github.io
SERVICE_api=api.example.com
SECRET_KEY=your-secret-key

# 2. Deploy to Railway (includes free credits)
```
[Deploy to Railway](https://railway.com?referralCode=ZIdvo-)
- Fork && deploy or
- Clone && railway up

```bash
# 3. Point DNS: yourdomain.com → your-proxy
```

**Usage:** `yourdomain.com/dev/` → `vicnasdev.github.io/`

## How It Works

The proxy rewrites URLs so JavaScript apps work transparently:
- Pathname reads see clean paths (no `/service/` prefix)
- Relative URLs get `/service/` prefix automatically
- Absolute URLs (APIs, CDNs) stay untouched

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_*` | - | Service mappings (e.g., `SERVICE_dev=example.com` or `SERVICE_api=api.example.com/base/path`) |
| `SERVICE_*_DESC` | _(optional)_ | Description for a service (e.g., `SERVICE_dev_DESC=Development site`) |
| `SERVICE_*_RANK` | `999` | Optional rank for ordering services (e.g., `SERVICE_api_RANK=1`) |
| `SECRET_KEY` | `change-me-in-production` | Django secret key |
| `DEBUG` | `false` | Verbose logs, no caching |
| `LOGS` | `false` | Enable `/_logs/` endpoint |
| `FIXES` | `false` | Show changelog on homepage |
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
