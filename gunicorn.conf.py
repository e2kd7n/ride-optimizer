import os

bind = f"{os.getenv('BIND_HOST', '127.0.0.1')}:{os.getenv('APP_PORT', '8083')}"
workers = int(os.getenv('GUNICORN_WORKERS', '1'))
# gthread instead of a second worker process: a slow/blocked request (e.g. a
# hanging Strava call) no longer serializes every other request behind it,
# without doubling the base memory footprint the way a second process would
# on the Pi's memory-limited container.
worker_class = 'gthread'
threads = int(os.getenv('GUNICORN_THREADS', '4'))
# 600, not 60: with preload_app off, the worker builds the whole app (every
# service's caches, ~75MB of route JSON at 8k activities) before its first
# heartbeat. On the Pi that now takes minutes, and at 60s gunicorn killed each
# worker mid-boot forever (2026-10-25). Under gthread the main thread keeps
# heartbeating while requests run on the other threads, so this only bounds
# boot and a truly wedged worker, not slow requests.
timeout = int(os.getenv('GUNICORN_TIMEOUT', '600'))
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
# Off: with a single worker, preloading only made the master hold its own
# ~220MB copy of the app (refcount writes defeat copy-on-write) on top of the
# worker's, inside the same container memory limit.
preload_app = False
# Worker recycling is OFF by default. With a single worker, a recycle kills
# every in-process background job (analysis, backfill, fetch — they run as
# threads in the worker and their state is in memory). Status polling burns
# ~500 requests in well under an hour, so once a full analysis outgrew that
# (8k activities) the nightly cron run was killed mid-way every night,
# ending "with status 'idle'". Set GUNICORN_MAX_REQUESTS to re-enable.
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '0'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '0'))