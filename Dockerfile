# ---- Stage 1: build the Python environment -------------------------------
# gcc/g++ live only here, as a fallback for any dependency without an arm64
# wheel. The runtime image copies the finished venv and never has a compiler
# (#677).
FROM python:3.11-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Install from the lock file, not requirements.txt: requirements.txt has floor
# pins (e.g. >=), so an upstream release would otherwise reach the Pi at the
# next auto-update with no change on our side (#677, #636). Regenerate the lock
# with the command in its header whenever requirements.txt changes; CI fails
# if the two drift apart.
COPY requirements.lock.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefer-binary -r requirements.lock.txt

# ---- Stage 2: runtime ----------------------------------------------------
FROM python:3.11-slim-bookworm

# /opt/venv first on PATH, so `python` / `gunicorn` (including the cron jobs'
# `podman exec <container> python ...`) resolve to the copied venv.
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_PORT=8083 \
    # numpy/scipy BLAS backends default to one thread per core, which
    # multiplies memory/CPU pressure inside the 512MB container on the Pi.
    # Analysis parallelism is governed by ANALYSIS_N_WORKERS instead.
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

# libcairo2/libpango*/libgdk-pixbuf/shared-mime-info/fonts-dejavu-core were
# only needed by weasyprint (legacy CLI PDF export, removed from
# requirements.txt in #498 Phase 2).
# curl: HEALTHCHECK. libffi8: runtime library for cffi/cryptography.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libffi8 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
# Fail the build, not the Pi, if the copied venv can't load its compiled deps.
RUN python -c "import flask, gunicorn, numpy, scipy, pandas, sklearn, cryptography, garth, anthropic"

WORKDIR /app

RUN mkdir -p data cache logs config htmlcov \
    && chmod 755 data cache logs config

COPY launch.py wsgi.py gunicorn.conf.py ./
COPY app/ ./app/
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/
COPY config/ ./config/
COPY cron/ ./cron/
COPY .env.example .

RUN useradd -m -u 1000 rideopt && chown -R rideopt:rideopt /app
USER rideopt

EXPOSE ${APP_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT}/api/status || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
