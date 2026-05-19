import os

bind = f"0.0.0.0:{os.getenv('APP_PORT', '8083')}"
workers = int(os.getenv('GUNICORN_WORKERS', '2'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '60'))
keepalive = 5
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
preload_app = True
