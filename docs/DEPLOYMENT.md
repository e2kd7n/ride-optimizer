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

The app is served over HTTPS by the bundled Caddy reverse proxy at `https://pi4.local` (or whatever `CADDY_SITE_ADDRESS` is set to) — see "HTTPS / TLS" below for the one-time browser trust step. `ride-optimizer` itself no longer publishes a host port; it's reachable from the LAN only through Caddy.

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

Default port **8083** does not conflict with common defaults (80, 443, 3000, 5000, 8000, 8080), but `ride-optimizer` no longer publishes it to the host at all — see "HTTPS / TLS" below. The `caddy` service does publish **443**; if another service on the Pi already holds that port, stop it or change `CADDY_SITE_ADDRESS`/the `caddy` service's `ports:` in a `docker-compose.override.yml`.

## HTTPS / TLS

The `caddy` service (`deploy/Caddyfile`) reverse-proxies HTTPS on port 443 to `ride-optimizer` over the compose-internal network; gunicorn/Flask never handle TLS directly (#526). This matters for browser APIs that require a [secure context](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts) — notably the Explore page's "Use My Location" button, which browsers refuse to run at all over plain HTTP on a non-localhost origin.

By default Caddy mints its own local CA and a leaf certificate for `pi4.local` (Caddy's `tls internal` directive) — no domain name or DNS provider required, and renewal is fully automatic. This is the right fit for a LAN-only personal deployment like this one; there's no public domain or Tailscale in play here, so the CA-signed path from issue #526 (real domain + certbot/DNS-01, or `tailscale cert`) doesn't apply unless that changes later.

**First-time setup on the Pi:**

1. `podman-compose up -d` as usual — Caddy generates its root CA and leaf cert on first start (persisted in `./caddy_data`, so this only happens once).
2. Visit `https://pi4.local` (or your LAN IP, or whatever you set `CADDY_SITE_ADDRESS` to in `.env`). Your browser will warn that the certificate authority isn't trusted — that's expected, since it's a private CA Caddy generated for this Pi.
3. Either click through the warning each time (fine for occasional use), or trust the CA once per device for a warning-free experience:
   ```bash
   podman exec ride-optimizer-caddy cat /data/caddy/pki/authorities/local/root.crt
   ```
   Copy that output to your device and add it as a trusted root certificate (Settings → trust store on iOS/Android; `certmgr.msc` → Trusted Root CAs on Windows; Keychain Access on macOS).

If `pi4.local` doesn't resolve on your network (mDNS/Avahi not reachable from that device), set `CADDY_SITE_ADDRESS=https://<pi-lan-ip>` in `.env` and restart — Caddy will mint a cert for the IP instead.

## Monitoring

```bash
# Live logs
podman-compose logs -f

# Container health and resource usage
podman-compose ps
podman stats ride-optimizer ride-optimizer-caddy

# Manual health check (self-signed cert, so -k)
curl -k https://pi4.local/api/status
```

## Backup and Restore

```bash
# Backup (caddy_data preserves the local CA so trusted devices stay trusted
# after a restore — omit it and Caddy just mints a new one, requiring
# re-trust per device)
tar -czf ~/backups/ride-optimizer-$(date +%Y%m%d).tar.gz data/ cache/ config/ caddy_data/ .env

# Restore
podman-compose down
tar -xzf ~/backups/ride-optimizer-YYYYMMDD.tar.gz
podman-compose up -d
```

## GHCR Package Visibility

After the first CI push, the package appears at `https://github.com/e2kd7n?tab=packages`. To allow unauthenticated pulls, set the package to **public** in the GitHub UI. Otherwise authenticate with a PAT that has `packages:read` scope (see Prerequisites above).

---

*Last Updated: 2026-09-20*
