# Path-Based Reverse Proxy

Simple reverse proxy using URL paths instead of subdomains.

## Quick Setup

1. **Create `.env` file:**
   ```bash
   SERVICE_api=api.up.railway.app
   SERVICE_calculum=calculum.up.railway.app
   
   SECRET_KEY=your-secret-key
   DEBUG=False
   ALLOWED_HOSTS=vicnas.me
   ```

2. [**Deploy to Railway**](https://railway.com?referralCode=ZIdvo-)

3. **Add custom domain** in Railway settings

4. **Update DNS** with Railway's records

## Usage

`/{service}/` routes to the domain configured in your `.env`

<!-- Examples:
- `https://vicnas.me/dash0/` → `https://dash0.up.railway.app/`
- `https://vicnas.me/api/users` → `https://api.up.railway.app/users` -->

## Limitations

- **No WebSocket support** - needs Nginx/Caddy