FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_PORT=8083

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi8 shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p data cache logs config htmlcov \
    && chmod 755 data cache logs config

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary \
        --only-binary=:all: numpy pandas scikit-learn scipy 2>/dev/null || \
    pip install --no-cache-dir numpy pandas scikit-learn scipy && \
    pip install --no-cache-dir -r requirements.txt

COPY launch.py wsgi.py gunicorn.conf.py ./
COPY app/ ./app/
COPY src/ ./src/
COPY static/ ./static/
COPY config/ ./config/
COPY cron/ ./cron/
COPY .env.example .

RUN useradd -m -u 1000 rideopt && chown -R rideopt:rideopt /app
USER rideopt

EXPOSE ${APP_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT}/api/status || exit 1

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
