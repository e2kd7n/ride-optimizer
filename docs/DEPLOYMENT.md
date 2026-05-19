# Deployment Guide — Raspberry Pi 4 via GHCR

Images are built by GitHub Actions and published to GitHub Container Registry (GHCR). The Pi pulls and runs the pre-built image — no on-device compilation required.

## Prerequisites

- Raspberry Pi 4 (2GB RAM minimum, 4GB+ recommended), running Raspberry Pi OS 64-bit
- Docker installed on the Pi (or Podman — see note below)
- Git, curl

```bash
# Install Docker on Raspberry Pi OS
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group membership to take effect
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
docker compose up -d

# Check status (healthy after ~20s)
docker compose ps
```

The app will be available at `http://<pi-ip>:8083`.

## Changing the Port

Set `APP_PORT` in `.env`:

```bash
APP_PORT=9000
```

Then restart:

```bash
docker compose up -d
```

The compose file uses `${APP_PORT:-8083}` throughout, so no file edits are needed.

## Updating

Push to `main` on GitHub → Actions builds a new image → on next Pi restart (or manually):

```bash
docker compose pull
docker compose up -d
```

The systemd service (see below) runs `--pull always` on every boot, so reboots automatically apply the latest image.

## Auto-Start on Boot (systemd)

The `deploy/ride-optimizer.service` unit file starts the container on boot and pulls the latest image each time.

### Installation

```bash
# Replace 'pi' with your actual username
sudo cp deploy/ride-optimizer.service /etc/systemd/system/
sudo sed -i 's/%i/pi/g' /etc/systemd/system/ride-optimizer.service

sudo systemctl daemon-reload
sudo systemctl enable ride-optimizer.service
sudo systemctl start ride-optimizer.service

# Verify
sudo systemctl status ride-optimizer.service
```

### Rootless Docker / Podman

If running rootless, use a user-level unit instead:

```bash
mkdir -p ~/.config/systemd/user/
cp deploy/ride-optimizer.service ~/.config/systemd/user/
# Edit WorkingDirectory to match your clone path
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

Then `docker compose up -d --build` will use your local source.

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
docker compose logs -f

# Container health and resource usage
docker compose ps
docker stats ride-optimizer

# Manual health check
curl http://localhost:8083/api/status
```

## Backup and Restore

```bash
# Backup
tar -czf ~/backups/ride-optimizer-$(date +%Y%m%d).tar.gz data/ cache/ config/ .env

# Restore
docker compose down
tar -xzf ~/backups/ride-optimizer-YYYYMMDD.tar.gz
docker compose up -d
```

## GHCR Package Visibility

After the first CI push, the package appears at `https://github.com/e2kd7n?tab=packages`. To allow `docker pull` without authentication on the Pi, set the package to **public** in the GitHub UI. Alternatively, authenticate with a Personal Access Token (PAT) that has `packages:read` scope:

```bash
echo $PAT | docker login ghcr.io -u e2kd7n --password-stdin
```

## Podman Compatibility

Replace `docker` with `podman` and `docker compose` with `podman-compose` in the commands above. The Dockerfile and compose file are fully compatible with Podman.

---

*Last Updated: 2026-05-18*
