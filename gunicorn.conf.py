import os

bind = f"{os.getenv('BIND_HOST', '127.0.0.1')}:{os.getenv('APP_PORT', '8083')}"
workers = int(os.getenv('GUNICORN_WORKERS', '1'))
# gthread instead of a second worker process: a slow/blocked request (e.g. a
# hanging Strava call) no longer serializes every other request behind it,
# without doubling the base memory footprint the way a second process would
# on the Pi's memory-limited container.
worker_class = 'gthread'
threads = int(os.getenv('GUNICORN_THREADS', '4'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '60'))
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
preload_app = True
# Worker recycling is OFF by default. With a single worker, a recycle kills
# every in-process background job (analysis, backfill, fetch — they run as
# threads in the worker and their state is in memory). Status polling burns
# ~500 requests in well under an hour, so once a full analysis outgrew that
# (8k activities) the nightly cron run was killed mid-way every night,
# ending "with status 'idle'". Set GUNICORN_MAX_REQUESTS to re-enable.
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '0'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '0'))