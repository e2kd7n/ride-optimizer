"""
Flask application factory for Ride Optimizer web platform.

This module creates and configures the Flask application instance using the
application factory pattern for better testability and configuration management.
"""

import os
import logging
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
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    
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
    from app.routes import dashboard, commute, planner, route_library, settings, api
    
    # Register blueprints with URL prefixes
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(commute.bp, url_prefix='/commute')
    app.register_blueprint(planner.bp, url_prefix='/planner')
    app.register_blueprint(route_library.bp, url_prefix='/routes')
    app.register_blueprint(settings.bp, url_prefix='/settings')
    app.register_blueprint(api.bp, url_prefix='/api')
    
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
