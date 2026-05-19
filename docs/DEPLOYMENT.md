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

The app will be available at `http://<pi-ip>:8083`.

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

Default port **8083** does not conflict with common defaults (80, 443, 3000, 5000, 8000, 8080). Change via `APP_PORT` in `.env` if needed.

## Monitoring

```bash
# Live logs
podman-compose logs -f

# Container health and resource usage
podman-compose ps
podman stats ride-optimizer

# Manual health check
curl http://localhost:8083/api/status
```

## Backup and Restore

```bash
# Backup
tar -czf ~/backups/ride-optimizer-$(date +%Y%m%d).tar.gz data/ cache/ config/ .env

# Restore
podman-compose down
tar -xzf ~/backups/ride-optimizer-YYYYMMDD.tar.gz
podman-compose up -d
```

## GHCR Package Visibility

After the first CI push, the package appears at `https://github.com/e2kd7n?tab=packages`. To allow unauthenticated pulls, set the package to **public** in the GitHub UI. Otherwise authenticate with a PAT that has `packages:read` scope (see Prerequisites above).

---

*Last Updated: 2026-05-18*
