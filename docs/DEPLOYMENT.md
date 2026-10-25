# Deployment Guide — Raspberry Pi 4 via GHCR

Images are built by GitHub Actions and published to GitHub Container Registry (GHCR). The Pi pulls and runs the pre-built image — no on-device compilation required.

## Prerequisites

- Raspberry Pi 4 (2GB RAM minimum, 4GB+ recommended), running Raspberry Pi OS 64-bit
- Podman and podman-compose installed on the Pi
- Git, curl

```bash
# Install Podman on Raspberry Pi OS
sudo apt-get update && sudo apt-get install -y podman podman-compose

# Authenticate with GHCR once — credentials stored globally
echo "YOUR_GITHUB_PAT" | podman login ghcr.io -u e2kd7n --password-stdin
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/e2kd7n/ride-optimizer.git
cd ride-optimizer

# Create .env from example and fill in your Strava credentials
cp .env.example .env
nano .env

# Pull and start
podman-compose up -d

# Check status (healthy after ~20s)
podman-compose ps
```

On pi4 the app is served at **`https://ride.local`** by the pi4 front door, a shared Caddy that lives in the separate `pi-scripts` repo (`pi4/front-door/`). See "HTTPS / TLS" below. `ride-optimizer` itself publishes only `127.0.0.1:18083` on the Pi's loopback, for the front door to proxy to; nothing on the LAN reaches it directly.

## Changing the Port

Set `APP_PORT` in `.env`:

```bash
APP_PORT=9000
```

Then restart:

```bash
podman-compose up -d
```

The compose file uses `${APP_PORT:-8083}` throughout, so no file edits are needed.

## Updating

Push to `main` on GitHub → Actions builds a new image → on next Pi restart (or manually):

```bash
podman-compose pull
podman-compose up -d
```

The systemd timer (see below) pulls nightly at 01:30 and redeploys only if the image changed.

## Auto-Update (systemd timer)

Install the nightly pull-and-redeploy timer:

```bash
chmod +x scripts/pi-auto-update.sh scripts/pi-update-setup.sh
./scripts/pi-update-setup.sh
```

Manual trigger:

```bash
./scripts/pi-auto-update.sh --force
```

### Rootless Podman

If running rootless, use a user-level unit:

```bash
mkdir -p ~/.config/systemd/user/
cp deploy/ride-optimizer.service ~/.config/systemd/user/
nano ~/.config/systemd/user/ride-optimizer.service

systemctl --user daemon-reload
systemctl --user enable ride-optimizer.service
systemctl --user start ride-optimizer.service

# Keep services running after logout
loginctl enable-linger $USER
```

## Local Development Build

To build from source instead of pulling from GHCR, create a `docker-compose.override.yml` (gitignored):

```yaml
# docker-compose.override.yml — local dev only, not committed
services:
  ride-optimizer:
    build:
      context: .
      dockerfile: Dockerfile
    image: ride-optimizer:dev
```

Then `podman-compose up -d --build` will use your local source.

## Data Persistence

Volumes mounted from the repo directory:

| Host path | Container path | Purpose |
|-----------|---------------|---------|
| `./data` | `/app/data` | Strava activity data |
| `./cache` | `/app/cache` | Geocoding, weather, route caches |
| `./logs` | `/app/logs` | Application logs |
| `./config` | `/app/config` | Configuration files |

## Coexisting with Other Services

The compose file uses bridge networking (not `host` mode), so ride-optimizer has its own network namespace. Port conflicts with other services (e.g., mealplanner) are explicit and caught at startup rather than at bind time.

The compose file publishes the app port on the Pi's **loopback only** (`127.0.0.1:18083` → container `${APP_PORT:-8083}`), so it can't collide with anything on the LAN side. 18083 rather than 8083 because the front door itself listens on host `:8083` to redirect old `http://pi4:8083` bookmarks. If you change it, change `pi4/front-door/Caddyfile` and `apps.json` in pi-scripts to match.

## HTTPS / TLS

TLS is terminated by the **pi4 front door**: a Caddy container in the `pi-scripts` repo (`pi4/front-door/`) that owns the Pi's `:80`/`:443` for every app and also serves the home dashboard at `http://pi4/`. It proxies `https://ride.local` to `127.0.0.1:18083`. gunicorn/Flask never handle TLS directly (#526). HTTPS matters here for browser APIs that require a [secure context](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts), notably the Explore page's "Use My Location" button, which browsers refuse to run over plain HTTP on a non-localhost origin.

Until 2026-10-25 this repo ran its own `caddy` service (`deploy/Caddyfile`) at `https://pi4.local`. That moved to pi-scripts when the Pi got a shared front door. Old addresses redirect: `https://pi4.local/<page>` and `http://pi4:8083/<page>` both 308 to `https://ride.local/<page>`.

The certificate comes from Caddy's own local CA (`tls internal`). The front door kept the CA this repo's Caddy generated, so devices that already trust it still do. To trust it on a new device, see "Certificates" in pi-scripts' `pi4/README.md`.

**Strava re-authorization:** the OAuth callback URL is built from the request host (`url_for(..., _external=True)`), so it is now `https://ride.local/...`. If Strava rejects a re-auth with a redirect-URI error, set the Strava API app's "Authorization Callback Domain" to `ride.local` at strava.com/settings/api. Routine token refreshes don't use the callback and aren't affected.

## Monitoring

```bash
# Live logs
podman-compose logs -f

# Container health and resource usage
podman-compose ps
podman stats ride-optimizer

# Manual health check — on the Pi, straight to the app:
curl -s http://127.0.0.1:18083/api/status
# ...or from the LAN through the front door (local CA, so -k):
curl -k https://ride.local/api/status
```

## Backup and Restore

```bash
# Backup (the local CA now lives with the front door in pi-scripts, not here)
tar -czf ~/backups/ride-optimizer-$(date +%Y%m%d).tar.gz data/ cache/ config/ .env

# Restore
podman-compose down
tar -xzf ~/backups/ride-optimizer-YYYYMMDD.tar.gz
podman-compose up -d
```

## GHCR Package Visibility

After the first CI push, the package appears at `https://github.com/e2kd7n?tab=packages`. To allow unauthenticated pulls, set the package to **public** in the GitHub UI. Otherwise authenticate with a PAT that has `packages:read` scope (see Prerequisites above).

---

*Last Updated: 2026-09-20*
