"""
Flask application factory for Ride Optimizer web platform.

This module creates and configures the Flask application instance using the
application factory pattern for better testability and configuration management.
"""

import os
import logging
from pathlib import Path
from flask import Flask
from flask_cors import CORS


def create_app(config_name='default'):
    """
    Application factory function.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        
    Returns:
        Configured Flask application instance
    """
    # Get project root directory (parent of app package)
    project_root = Path(__file__).parent.parent
    static_folder = project_root / 'static'
    
    app = Flask(__name__,
                template_folder='templates',
                static_folder=str(static_folder),
                static_url_path='')
    
    # Load configuration
    from app.config import config as config_dict
    app.config.from_object(config_dict[config_name])
    
    # Initialize database
    from app.models import db
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Enable CORS for API endpoints
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Configure logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Initialize and start scheduler (unless in testing mode)
    if not app.testing:
        try:
            from app.scheduler import start_scheduler
            start_scheduler(app)
            app.logger.info("Background scheduler started")
        except Exception as e:
            app.logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            app.logger.warning("Application will continue without background scheduler")
            # App continues without scheduler - degraded mode
    
    # Log startup
    app.logger.info(f"Ride Optimizer web platform initialized (config: {config_name})")
    
    return app


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Production logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/web_platform.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Ride Optimizer web platform startup')


def register_blueprints(app):
    """Register Flask blueprints for different sections of the application."""
    from flask import send_from_directory, current_app
    from app.api import map_api, maps_api
    
    # Serve static HTML files (Issue #257 - Epic #237 UI/UX Redesign)
    @app.route('/')
    def index():
        """Serve the main application page with 3-tab navigation."""
        return send_from_directory(current_app.static_folder, 'index.html')
    
    @app.route('/routes')
    @app.route('/routes.html')
    def routes_page():
        """Serve routes page."""
        return send_from_directory(current_app.static_folder, 'routes.html')
    
    @app.route('/settings')
    @app.route('/settings.html')
    def settings_page():
        """Serve settings page."""
        return send_from_directory(current_app.static_folder, 'settings.html')
    
    # Register API blueprints only
    from app.routes_DEPRECATED_FLASK import api
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(map_api.bp)  # Map API (already has /api/map prefix)
    app.register_blueprint(maps_api.bp)  # Maps API for page-level data (already has /api/maps prefix)
    
    app.logger.info('Registered all blueprints')


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""
    from flask import render_template, jsonify
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        if '/api/' in str(error):
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        app.logger.error(f'Internal server error: {error}')
        if '/api/' in str(error):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors."""
        if '/api/' in str(error):
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403

# Made with Bob
