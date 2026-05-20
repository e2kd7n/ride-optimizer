"""WSGI entry point — gunicorn runs: gunicorn --config gunicorn.conf.py wsgi:app"""
from launch import app  # noqa: F401  (re-exported for gunicorn)

if __name__ == '__main__':
    import os
    port = int(os.getenv('APP_PORT', 8083))
    app.run(host='0.0.0.0', port=port, debug=False)
