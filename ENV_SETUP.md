# Environment Configuration Guide

This project uses environment-specific configuration files to manage settings across local development, staging, and production environments.

## File Structure

```
.env.example              # Template (committed to git)
.env.production.example   # Production template (committed to git)
.env.local               # Local development (gitignored)
.env.production          # Production secrets (gitignored)
```

## Setup Instructions

### Local Development

1. **Copy the example file:**
   ```bash
   cp .env.example .env.local
   ```

2. **Edit `.env.local` with your settings:**
   ```bash
   FLASK_ENV=development
   SECRET_KEY=your-local-dev-key
   DATABASE_URL=postgresql://tournament:tournament123@postgres:5432/tournament_db
   DOMAIN=tournament.local
   ```

3. **Start services:**
   ```bash
   docker-compose up --build
   ```

4. **Access via HTTPS:**
   ```
   https://localhost
   ```

### Production Deployment

1. **Copy the production template:**
   ```bash
   cp .env.production.example .env.production
   ```

2. **Edit `.env.production` with production values:**
   ```bash
   FLASK_ENV=production
   SECRET_KEY=$(openssl rand -hex 32)  # Generate strong key
   DATABASE_URL=postgresql://user:pass@prod-db:5432/tournament_db
   DOMAIN=yourdomain.com
   GCP_PROJECT_ID=your-project-id
   ```

3. **Deploy with production compose file:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | Yes | `development` | Flask environment mode |
| `SECRET_KEY` | Yes | - | Flask secret key for sessions |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `DOMAIN` | No | `tournament.local` | Domain for HTTPS (Caddy) |
| `GCP_PROJECT_ID` | No | - | Google Cloud project for Pub/Sub |
| `GCP_REGION` | No | `us-central1` | GCP region |

## Docker Compose Files

### `docker-compose.yml` (Local Development)
- Uses `.env.local`
- Exposes PostgreSQL port 5432 for debugging
- Volume mounts for hot-reload
- Self-signed HTTPS certificates

### `docker-compose.prod.yml` (Production)
- Uses `.env.production`
- No exposed database ports
- No volume mounts
- Let's Encrypt HTTPS certificates
- Restart policies enabled

## Security Best Practices

✅ **Never commit `.env.local` or `.env.production`** - They contain secrets
✅ **Use strong random keys** - Generate with `openssl rand -hex 32`
✅ **Different secrets per environment** - Don't reuse keys
✅ **Rotate secrets regularly** - Update production keys periodically
✅ **Use managed databases in production** - Don't run PostgreSQL in Docker

## Generating Secure Keys

```bash
# Generate a secure SECRET_KEY
openssl rand -hex 32

# Or use Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Switching Environments

### Local → Production
```bash
# Stop local
docker-compose down

# Start production
docker-compose -f docker-compose.prod.yml up -d
```

### Check Current Environment
```bash
# View orchestrator environment
docker-compose exec orchestrator env | grep FLASK_ENV

# View Caddy domain
docker-compose exec caddy env | grep DOMAIN
```

## Troubleshooting

### "Environment variable not set" error
- Ensure `.env.local` exists and has all required variables
- Check file is in project root directory
- Restart containers: `docker-compose restart`

### Database connection fails
- Verify `DATABASE_URL` format: `postgresql://user:pass@host:port/db`
- Check PostgreSQL is running: `docker-compose ps postgres`
- View logs: `docker-compose logs postgres`

### HTTPS certificate issues
- Verify `DOMAIN` is set correctly
- For production, ensure DNS points to your server
- For local, use `localhost` or add domain to `/etc/hosts`

## Migration Checklist

When deploying to production:

- [ ] Copy `.env.production.example` to `.env.production`
- [ ] Generate new `SECRET_KEY`
- [ ] Set production `DATABASE_URL`
- [ ] Set actual `DOMAIN` name
- [ ] Configure GCP credentials (if using Pub/Sub)
- [ ] Test with `docker-compose -f docker-compose.prod.yml config`
- [ ] Deploy with `docker-compose -f docker-compose.prod.yml up -d`
- [ ] Verify HTTPS works: `curl -I https://yourdomain.com`
- [ ] Check logs: `docker-compose -f docker-compose.prod.yml logs`
