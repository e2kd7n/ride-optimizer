"""WSGI entry point — gunicorn runs: gunicorn --config gunicorn.conf.py wsgi:app"""
from launch import app  # noqa: F401  (re-exported for gunicorn)

if __name__ == '__main__':
    import os
    port = int(os.getenv('APP_PORT', 8083))
    host = os.getenv('BIND_HOST', '127.0.0.1')
    app.run(host=host, port=port, debug=False)
