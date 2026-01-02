# HTTPS Setup Guide

This application uses **Caddy** as a reverse proxy to provide automatic HTTPS everywhere - in development, local, and production environments.

## How It Works

1. **Caddy sits in front of Flask** - All traffic goes through Caddy on ports 80/443
2. **Flask runs on internal port 5000** - Not exposed to the host
3. **Automatic TLS certificates**:
   - **Local/Dev**: Self-signed certificates (automatic)
   - **Production**: Let's Encrypt certificates (automatic when using real domain)

## Quick Start

### Local Development (localhost)

```bash
# Start all services
docker-compose up --build

# Access via HTTPS
https://localhost

# Your browser will warn about self-signed cert - this is expected
# Click "Advanced" → "Proceed to localhost (unsafe)" to continue
```

### Production Deployment

```bash
# Set your domain
export DOMAIN=yourdomain.com

# Or create .env file
echo "DOMAIN=yourdomain.com" > .env

# Start services
docker-compose up -d

# Caddy automatically gets Let's Encrypt certificate
# Access via: https://yourdomain.com
```

## Configuration Files

### Caddyfile
Located at `./Caddyfile` - defines reverse proxy rules:
- `localhost` → Self-signed cert for local dev
- `{$DOMAIN}` → Let's Encrypt cert for production

### docker-compose.yml
- **Caddy service**: Handles HTTPS on ports 80/443
- **Orchestrator service**: Internal only (no exposed ports)
- **ProxyFix middleware**: Flask correctly handles X-Forwarded-* headers

## Security Features

✅ **All traffic encrypted** - HTTP automatically redirects to HTTPS
✅ **No IP logging** - Application doesn't track client IPs
✅ **Secure headers** - Caddy adds security headers automatically
✅ **Certificate auto-renewal** - Let's Encrypt certs renew automatically

## Trusting Self-Signed Certificates (Local Dev)

### macOS
```bash
# Export Caddy's root CA
docker-compose exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt

# Add to system keychain
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain caddy-root.crt
```

### Linux
```bash
# Export root CA
docker-compose exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt

# Add to trusted certificates
sudo cp caddy-root.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

### Windows
```bash
# Export root CA
docker-compose exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt

# Double-click caddy-root.crt and install to "Trusted Root Certification Authorities"
```

## Custom Domain (Local Dev)

To use a custom domain locally:

```bash
# Add to /etc/hosts (macOS/Linux) or C:\Windows\System32\drivers\etc\hosts (Windows)
127.0.0.1 tournament.local

# Set domain in .env
DOMAIN=tournament.local

# Restart services
docker-compose restart caddy

# Access via
https://tournament.local
```

## Troubleshooting

### "Connection refused" error
- Check Caddy is running: `docker-compose ps caddy`
- Check logs: `docker-compose logs caddy`

### Certificate errors
- Clear browser cache and restart
- Verify Caddyfile syntax: `docker-compose exec caddy caddy validate --config /etc/caddy/Caddyfile`

### Port conflicts
- Ensure ports 80/443 are not in use: `lsof -i :443` (macOS/Linux)
- Stop other web servers (nginx, apache, etc.)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN` | `tournament.local` | Domain name for production |
| `FLASK_ENV` | `development` | Flask environment |
| `SECRET_KEY` | (required) | Flask secret key |

## Architecture

```
Internet/Browser
       ↓
   [Caddy :443]  ← HTTPS termination, TLS certificates
       ↓
[Flask :5000]     ← Internal HTTP (not exposed)
       ↓
 [PostgreSQL]
```

## Why This Approach?

1. **Simple**: One config file, automatic certificates
2. **Consistent**: Same setup for dev, local, and prod
3. **Secure**: HTTPS everywhere, no manual cert management
4. **Fast**: Caddy is lightweight and efficient
5. **Privacy**: No IP tracking, encrypted traffic

## Additional Resources

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Flask ProxyFix](https://flask.palletsprojects.com/en/2.3.x/deploying/proxy_fix/)
