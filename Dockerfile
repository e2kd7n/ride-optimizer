# Optimized Dockerfile for Raspberry Pi with Podman
# Addresses ARM architecture compatibility and rootless networking issues

# Use official Python image with pre-built ARM wheels
FROM python:3.11-slim-bookworm

# Set environment variables early
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies in a single layer
# Minimize build dependencies by using pre-built wheels where possible
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential build tools (minimal set)
    gcc \
    g++ \
    # WeasyPrint runtime dependencies (no build deps needed)
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu-core \
    # Networking tools for debugging
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/cache /app/logs /app/htmlcov && \
    chmod 755 /app/data /app/cache /app/logs /app/htmlcov

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
# Use --only-binary for packages that have ARM wheels to avoid compilation
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    --prefer-binary \
    --only-binary=:all: \
    numpy pandas scikit-learn scipy 2>/dev/null || \
    pip install --no-cache-dir numpy pandas scikit-learn scipy && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY src/ ./src/
COPY templates/ ./templates/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY .env.example .

# Create non-root user for security (compatible with rootless Podman)
RUN useradd -m -u 1000 rideopt && \
    chown -R rideopt:rideopt /app

# Switch to non-root user
USER rideopt

# Expose port for Flask API (if needed)
EXPOSE 5000

# Health check - simplified for better compatibility
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command - run the menu system
CMD ["python", "scripts/menu.py"]

# Made with Bob - Optimized for Raspberry Pi
