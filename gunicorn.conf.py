import os

bind = f"{os.getenv('BIND_HOST', '127.0.0.1')}:{os.getenv('APP_PORT', '8083')}"
workers = int(os.getenv('GUNICORN_WORKERS', '1'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '60'))
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
preload_app = True
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '500'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '50'))