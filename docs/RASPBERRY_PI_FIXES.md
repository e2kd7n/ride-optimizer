# Raspberry Pi Build Fixes

This document explains the fixes applied to resolve Podman build issues on Raspberry Pi.

## Problem: `slirp4netns failed` Error

### Root Cause
The error `error running container: did not get container start message from parent: EOF` followed by `slirp4netns failed` occurs due to networking issues with rootless Podman on ARM architecture, particularly during the build process when installing packages.

### Solutions Implemented

#### 1. Optimized Dockerfile
**File**: `Dockerfile`

**Changes**:
- Removed multi-stage build to reduce complexity
- Minimized build dependencies (removed gfortran, libopenblas-dev, liblapack-dev)
- Use `--prefer-binary` and `--only-binary` flags to prefer pre-built ARM wheels
- Simplified package installation to reduce network calls
- Single-stage build reduces intermediate container networking issues

**Key optimizations**:
```dockerfile
# Use pre-built wheels to avoid compilation
RUN pip install --no-cache-dir \
    --prefer-binary \
    --only-binary=:all: \
    numpy pandas scikit-learn scipy 2>/dev/null || \
    pip install --no-cache-dir numpy pandas scikit-learn scipy
```

#### 2. Docker Compose Network Configuration
**File**: `docker-compose.yml`

**Changes**:
- Changed `network_mode` from `bridge` to `host`
- Host networking avoids slirp4netns entirely for rootless containers

```yaml
# Network mode - host mode avoids slirp4netns issues on Raspberry Pi
network_mode: host
```

**Trade-off**: Port mapping is ignored with host networking, but the container can access all host ports directly.

#### 3. Build Script with Network Workaround
**File**: `scripts/build_pi.sh`

**Features**:
- Automatically uses `--network=host` flag during build
- Detects ARM architecture
- Checks for required tools (podman, podman-compose)
- Provides helpful error messages and troubleshooting tips
- Handles both podman-compose and direct podman builds

**Usage**:
```bash
chmod +x scripts/build_pi.sh
./scripts/build_pi.sh
```

## Alternative Solutions

If the above fixes don't work, try these alternatives:

### Option 1: Build as Root
```bash
sudo podman build --network=host -t ride-optimizer:latest .
```

**Note**: This bypasses rootless networking issues but requires root privileges.

### Option 2: Increase System Resources
```bash
# Check current resources
free -h
df -h

# Increase swap (for Pi with <4GB RAM)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Option 3: Configure Podman for Better Rootless Support
```bash
# Edit /etc/containers/containers.conf
sudo nano /etc/containers/containers.conf

# Add or modify:
[network]
network_backend = "netavark"  # or "cni"
```

### Option 4: Use Docker Instead of Podman
If Podman continues to have issues, Docker is an alternative:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Logout and login again, then:
docker-compose build
docker-compose up -d
```

## Technical Details

### Why slirp4netns Fails on Raspberry Pi

1. **ARM Architecture**: slirp4netns has known issues on ARM, especially ARM32
2. **Rootless Networking**: Rootless containers use slirp4netns for network isolation
3. **Build Process**: Heavy network activity during `apt-get` and `pip install` can overwhelm slirp4netns
4. **Resource Constraints**: Raspberry Pi's limited resources can cause timeouts

### Why Host Networking Works

- **Bypasses slirp4netns**: Uses host's network stack directly
- **Better Performance**: No network translation overhead
- **Simpler**: Fewer moving parts to fail
- **Trade-off**: Less isolation, but acceptable for personal/development use

### Why Pre-built Wheels Help

- **Avoid Compilation**: Building numpy/scipy from source on ARM takes 30+ minutes
- **Reduce Network Load**: Fewer package downloads during build
- **Faster Builds**: 5-10 minutes instead of 30+ minutes
- **Less Memory**: Compilation requires significant RAM

## Verification

After applying fixes, verify the build works:

```bash
# Clean build
podman rmi ride-optimizer:latest 2>/dev/null || true

# Build with script
./scripts/build_pi.sh

# Or manual build
podman build --network=host -t ride-optimizer:latest .

# Verify image exists
podman images | grep ride-optimizer

# Test run
podman run --rm ride-optimizer:latest python -c "import numpy, pandas, sklearn; print('Success!')"
```

## Performance Expectations

### Raspberry Pi 4 (4GB RAM)
- Build time: 10-15 minutes
- Memory usage: 500MB-1GB during build
- Runtime memory: 200-400MB

### Raspberry Pi 3B+ (1GB RAM)
- Build time: 20-30 minutes
- Memory usage: 700MB-1GB during build (requires swap)
- Runtime memory: 200-400MB

## Additional Resources

- [Podman Rootless Networking](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md)
- [slirp4netns Issues](https://github.com/rootless-containers/slirp4netns/issues)
- [Raspberry Pi Docker/Podman Guide](https://www.raspberrypi.com/documentation/computers/containers.html)

## Support

If you continue to experience issues:

1. Check system resources: `free -h` and `df -h`
2. Check Podman logs: `journalctl --user -u podman`
3. Try building as root: `sudo podman build --network=host -t ride-optimizer:latest .`
4. Consider using Docker instead of Podman
5. Open an issue with full error logs

---

*Last Updated: 2026-05-06*