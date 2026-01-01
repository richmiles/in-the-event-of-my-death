# Deployment (DigitalOcean droplet)

This document describes a v0 deployment setup using a DigitalOcean droplet, Docker Compose, and Caddy.

Goals:
- Automated deployments via GitHub Actions
- Same-origin API (`/api/*`) to avoid CORS complexity
- SQLite for v0 with backup-before-migrate
- Locked-down deploy access (least privilege)

## Architecture

- **Droplet** runs Docker Compose:
  - `web` (Caddy + frontend static assets)
  - `backend` (FastAPI)
- **Caddy** terminates TLS and reverse-proxies:
  - `/api/*` and `/health` → backend
  - everything else → frontend static files with SPA fallback

Compose files live in `deploy/`.

## One-time droplet setup (prod)

1. Create an Ubuntu LTS droplet.
2. Install Docker + Compose plugin.
3. Create directories:
   - `/opt/ieomd/` (deployment directory)
   - `/var/lib/ieomd/` (SQLite data)
   - `/var/backups/ieomd/` (SQLite backups)
4. Copy these files to `/opt/ieomd/`:
   - `deploy/docker-compose.yml`
   - `deploy/docker-compose.staging.yml` (staging only)
   - `deploy/Caddyfile` (if you want to override baked-in config)
5. Create `/opt/ieomd/.env` with at least:
   - `SITE_HOST=ieomd.com`
   - `SITE_ADDRESS=ieomd.com, www.ieomd.com` (Caddy site label(s))
   - `DATA_DIR=/var/lib/ieomd`
   - `DATABASE_URL=sqlite:////data/secrets.db`
6. Ensure `/opt/ieomd` contains a compose override if needed.

## Locked-down deploy user

Recommended approach:
- Create a `deploy` user that cannot open an interactive shell.
- Install the deploy script as root: `/usr/local/bin/ieomd-deploy` from `deploy/remote/ieomd-deploy`.
- In `authorized_keys`, force the command to run `sudo /usr/local/bin/ieomd-deploy ...` and disable PTY/port-forwarding.
- In sudoers, allow only that command for the deploy user.

## GitHub Actions secrets

You’ll need repository secrets for staging and production:

- `STAGING_SSH_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY`, `STAGING_SSH_KNOWN_HOSTS`
- `STAGING_SITE_HOST` (e.g. `staging.ieomd.com`)
- `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY`, `PROD_SSH_KNOWN_HOSTS`
- `PROD_SITE_HOST` (e.g. `ieomd.com`)

## GHCR image pulls

The droplet must be able to pull images from GHCR:

- Easiest: make the GHCR packages public.
- If packages are private: authenticate on the droplet (one-time):
  - Create a GitHub token with `read:packages`
  - On the droplet: `docker login ghcr.io`

## Deployment workflows

- Staging deploy runs automatically on merge to `main` (after checks and image build).
- Production deploy is manual and gated by GitHub Environments approval.

## SQLite migration + rollback

Production deploy performs:
1. Copy DB file to `/var/backups/ieomd/` with a timestamp.
2. Run `alembic upgrade head`.
3. Restart services.

Rollback plan:
- Restore the DB backup file and redeploy the previous image tag.
