# Deployment Guide - Raspberry Pi with Podman

This guide covers deploying the Ride Optimizer application in a Podman container on a Raspberry Pi.

## Prerequisites

### Hardware Requirements
- **Raspberry Pi 4** (2GB RAM minimum, 4GB+ recommended)
- **Raspberry Pi 3B+** (works but slower)
- **Storage**: 8GB+ SD card (16GB+ recommended)
- **Network**: Ethernet or WiFi connection

### Software Requirements
- **Raspberry Pi OS** (64-bit recommended for better performance)
- **Podman** and **podman-compose** installed
- **Git** (for cloning the repository)

## Quick Start

### 1. Install Podman on Raspberry Pi

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Podman
sudo apt-get install -y podman

# Install podman-compose
sudo apt-get install -y python3-pip
pip3 install podman-compose

# Verify installation
podman --version
podman-compose --version

# Enable podman socket (optional, for systemd integration)
systemctl --user enable --now podman.socket
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ride-optimizer.git
cd ride-optimizer

# Create .env file from example
cp .env.example .env

# Edit .env with your Strava API credentials
nano .env
```

**Required environment variables:**
```bash
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
```

### 3. Build and Run with Podman

**Option A: Using the optimized build script (Recommended for Raspberry Pi)**

```bash
# Run the Raspberry Pi optimized build script
./scripts/build_pi.sh

# Start the container
podman-compose up -d

# View logs
podman-compose logs -f

# Access the interactive menu
podman-compose exec ride-optimizer python scripts/menu.py
```

**Option B: Manual build with network workaround**

```bash
# Build with host network to avoid slirp4netns issues
podman build --network=host -t ride-optimizer:latest .

# Or with podman-compose
podman-compose build

# Start the container
podman-compose up -d

# View logs
podman-compose logs -f

# Access the interactive menu
podman-compose exec ride-optimizer python scripts/menu.py
```

### Alternative: Using Podman Directly (without compose)

```bash
# Build the image
podman build -t ride-optimizer:latest .

# Create volumes for persistent data
podman volume create ride-optimizer-data
podman volume create ride-optimizer-cache
podman volume create ride-optimizer-logs

# Run the container
podman run -d \
  --name ride-optimizer \
  --env-file .env \
  -v ./data:/app/data:Z \
  -v ./cache:/app/cache:Z \
  -v ./logs:/app/logs:Z \
  -v ./config:/app/config:Z \
  -p 8083:8083 \
  --memory=1g \
  --cpus=2 \
  ride-optimizer:latest

# Access the menu
podman exec -it ride-optimizer python scripts/menu.py
```

## Container Management

### Basic Commands with podman-compose

```bash
# Start container
podman-compose up -d

# Stop container
podman-compose down

# Restart container
podman-compose restart

# View logs
podman-compose logs -f

# Check container status
podman-compose ps

# Access container shell
podman-compose exec ride-optimizer bash

# Run the menu system
podman-compose exec ride-optimizer python scripts/menu.py

# Run main application
podman-compose exec ride-optimizer python main.py
```

### Basic Commands with Podman

```bash
# Start container
podman start ride-optimizer

# Stop container
podman stop ride-optimizer

# Restart container
podman restart ride-optimizer

# View logs
podman logs -f ride-optimizer

# Check container status
podman ps -a

# Access container shell
podman exec -it ride-optimizer bash

# Run the menu system
podman exec -it ride-optimizer python scripts/menu.py

# Remove container
podman rm ride-optimizer

# Remove image
podman rmi ride-optimizer:latest
```

### Interactive Mode

To use the interactive menu system:

```bash
# Attach to running container
podman attach ride-optimizer

# Or run in interactive mode
podman run -it --rm \
  --env-file .env \
  -v ./data:/app/data:Z \
  -v ./cache:/app/cache:Z \
  -v ./logs:/app/logs:Z \
  -v ./config:/app/config:Z \
  ride-optimizer:latest \
  python scripts/menu.py
```

## Data Persistence

The following directories are mounted as volumes for data persistence:

- **`./data`** - Strava activity data and analysis results
- **`./cache`** - Geocoding, weather, and route caches
- **`./logs`** - Application logs
- **`./config`** - Configuration files

**Note**: The `:Z` suffix on volume mounts enables SELinux relabeling for proper access.

## Podman-Specific Features

### Rootless Containers

Podman runs containers without root privileges by default, which is more secure:

```bash
# Check if running rootless
podman info | grep rootless

# Run as current user (default)
podman run --user $(id -u):$(id -g) ...
```

### Pod Management

You can run the application in a Podman pod for better organization:

```bash
# Create a pod
podman pod create --name ride-optimizer-pod -p 8083:8083

# Run container in the pod
podman run -d \
  --pod ride-optimizer-pod \
  --name ride-optimizer \
  --env-file .env \
  -v ./data:/app/data:Z \
  -v ./cache:/app/cache:Z \
  -v ./logs:/app/logs:Z \
  -v ./config:/app/config:Z \
  ride-optimizer:latest

# Manage the entire pod
podman pod start ride-optimizer-pod
podman pod stop ride-optimizer-pod
podman pod rm ride-optimizer-pod
```

### Generate Systemd Service

Podman can generate systemd service files automatically:

```bash
# Generate systemd service file
podman generate systemd --new --name ride-optimizer > ~/.config/systemd/user/ride-optimizer.service

# Enable and start service
systemctl --user enable ride-optimizer.service
systemctl --user start ride-optimizer.service

# Check status
systemctl --user status ride-optimizer.service

# Enable linger (keep services running after logout)
loginctl enable-linger $USER
```

## Performance Optimization

### For Raspberry Pi 3/4

Resource limits can be set directly in the run command:

```bash
podman run -d \
  --name ride-optimizer \
  --memory=1g \
  --memory-swap=2g \
  --cpus=2 \
  --cpu-shares=1024 \
  ...
```

### Adjust for Your Hardware

**For Raspberry Pi 3B+:**
```bash
--memory=512m --cpus=1
```

**For Raspberry Pi 4 (4GB+):**
```bash
--memory=2g --cpus=3
```

## Troubleshooting

### Build Issues

**Problem**: `slirp4netns failed` error during build
```bash
# Solution 1: Use host networking (recommended)
podman build --network=host -t ride-optimizer:latest .

# Solution 2: Build as root
sudo podman build -t ride-optimizer:latest .

# Solution 3: Use the optimized build script
./scripts/build_pi.sh
```

**Problem**: Build takes too long or fails
```bash
# Use the optimized Raspberry Pi build script
./scripts/build_pi.sh

# Or build with more verbose output
podman build --network=host --log-level=debug -t ride-optimizer:latest .

# Or build with no cache
podman build --network=host --no-cache -t ride-optimizer:latest .
```

**Problem**: Out of memory during build
```bash
# Check current memory and swap
free -h

# Increase swap space (recommended for Pi with <4GB RAM)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048 (or 4096 for Pi 3)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Verify new swap size
free -h

# Then retry build
./scripts/build_pi.sh
```

**Problem**: `error running container: EOF` during build
```bash
# This is related to slirp4netns networking issues
# Solution: Use host networking
podman build --network=host -t ride-optimizer:latest .

# Or use the build script which handles this automatically
./scripts/build_pi.sh
```

### Runtime Issues

**Problem**: Container exits immediately
```bash
# Check logs
podman logs ride-optimizer

# Run in foreground to see errors
podman run -it --rm \
  --env-file .env \
  -v ./data:/app/data:Z \
  ride-optimizer:latest
```

**Problem**: Permission denied errors with volumes
```bash
# Fix ownership of data directories
sudo chown -R $USER:$USER data cache logs config

# Or use :Z suffix for SELinux relabeling
-v ./data:/app/data:Z
```

**Problem**: Cannot connect to Strava API
```bash
# Verify .env file exists and has correct credentials
cat .env

# Check network connectivity
podman exec ride-optimizer ping -c 3 www.strava.com
```

**Problem**: SELinux denials
```bash
# Check SELinux status
getenforce

# Temporarily set to permissive for testing
sudo setenforce 0

# Or use :Z suffix on all volume mounts
```

### Performance Issues

**Problem**: Application runs slowly
```bash
# Monitor resource usage
podman stats ride-optimizer

# Check Raspberry Pi temperature
vcgencmd measure_temp

# Ensure adequate cooling
```

## Updating the Application

```bash
# Pull latest changes
git pull origin main

# Stop and remove old container
podman stop ride-optimizer
podman rm ride-optimizer

# Rebuild image
podman build -t ride-optimizer:latest .

# Start new container
podman run -d \
  --name ride-optimizer \
  --env-file .env \
  -v ./data:/app/data:Z \
  -v ./cache:/app/cache:Z \
  -v ./logs:/app/logs:Z \
  -v ./config:/app/config:Z \
  ride-optimizer:latest
```

## Backup and Restore

### Backup Data

```bash
# Create backup directory
mkdir -p ~/backups

# Backup data, cache, and config
tar -czf ~/backups/ride-optimizer-$(date +%Y%m%d).tar.gz \
  data/ cache/ config/ .env

# List backups
ls -lh ~/backups/
```

### Restore Data

```bash
# Stop container
podman stop ride-optimizer

# Extract backup
tar -xzf ~/backups/ride-optimizer-YYYYMMDD.tar.gz

# Start container
podman start ride-optimizer
```

### Export/Import Container Images

```bash
# Export image to file
podman save -o ride-optimizer.tar ride-optimizer:latest

# Import image on another system
podman load -i ride-optimizer.tar
```

## Security Considerations

1. **Rootless by default**: Podman runs containers without root privileges
2. **Keep credentials secure**: Never commit `.env` file to git
3. **Regular updates**: Keep Podman and Raspberry Pi OS updated
4. **SELinux**: Use `:Z` suffix on volume mounts for proper labeling
5. **Token encryption**: The app uses encrypted token storage by default

## Advanced Configuration

### Custom Configuration

Edit `config/config.yaml` to customize:
- Analysis parameters
- Cache settings
- Report generation options

### Running as a Systemd Service

Using Podman's built-in systemd integration:

```bash
# Create container with systemd restart policy
podman run -d \
  --name ride-optimizer \
  --restart=always \
  --env-file .env \
  -v ./data:/app/data:Z \
  -v ./cache:/app/cache:Z \
  -v ./logs:/app/logs:Z \
  -v ./config:/app/config:Z \
  ride-optimizer:latest

# Generate systemd service
mkdir -p ~/.config/systemd/user/
podman generate systemd --new --name ride-optimizer \
  > ~/.config/systemd/user/ride-optimizer.service

# Enable and start
systemctl --user daemon-reload
systemctl --user enable ride-optimizer.service
systemctl --user start ride-optimizer.service

# Enable linger (keep running after logout)
loginctl enable-linger $USER

# Check status
systemctl --user status ride-optimizer.service
```

## Monitoring

### View Resource Usage

```bash
# Real-time stats
podman stats ride-optimizer

# Container logs
podman logs -f --tail=100 ride-optimizer

# System resources
htop
```

### Health Checks

The container includes a health check that runs every 30 seconds:

```bash
# Check health status
podman healthcheck run ride-optimizer

# View health check logs
podman inspect ride-optimizer | grep -A 10 Health
```

## Podman vs Docker Compatibility

The provided `Dockerfile` and `docker-compose.yml` work with both Docker and Podman:

- **Dockerfile**: Fully compatible with Podman
- **docker-compose.yml**: Use `podman-compose` instead of `docker-compose`
- **Commands**: Replace `docker` with `podman` in most cases

### Key Differences

| Feature | Docker | Podman |
|---------|--------|--------|
| Root required | Yes (daemon) | No (rootless) |
| Daemon | Required | Daemonless |
| Compose | docker-compose | podman-compose |
| Systemd | Manual setup | Built-in generation |
| Security | Good | Better (rootless) |

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review [troubleshooting section](#troubleshooting)
- Check container logs: `podman logs ride-optimizer`
- Podman documentation: https://docs.podman.io/

---

*Last Updated: 2026-05-06*