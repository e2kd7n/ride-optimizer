"""
WSGI entry point for the Ride Optimizer web application.

This file is used by WSGI servers (Gunicorn, uWSGI, etc.) to run the application.
For development, use: flask run
For production, use: gunicorn wsgi:app
"""

import os
from app import create_app

# Determine environment from environment variable
config_name = os.getenv('FLASK_ENV', 'development')

# Create the Flask application
app = create_app(config_name)

if __name__ == '__main__':
    # This block is only executed when running directly with Python
    # For development: python wsgi.py
    # For production, use a proper WSGI server instead
    
    debug = config_name == 'development'
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )

# Made with Bob
