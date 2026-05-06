"""
Configuration classes for Flask application.

Provides different configurations for development, production, and testing environments.
"""

import os
from pathlib import Path


class Config:
    """Base configuration class with common settings."""
    
    # Application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    CACHE_DIR = BASE_DIR / 'cache'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Ensure directories exist
    DATA_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Database (SQLite for personal platform)
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATA_DIR / "ride_optimizer.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = str(CACHE_DIR / 'flask_sessions')
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # File upload settings (for future GPX import)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = str(DATA_DIR / 'uploads')
    
    # Pagination
    ROUTES_PER_PAGE = 20
    ACTIVITIES_PER_PAGE = 50
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # API rate limiting (for future external API endpoints)
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = 'memory://'
    
    # Strava API configuration (loaded from existing config)
    STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
    STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'
    
    # Disable CSRF for easier API testing in development
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration (Raspberry Pi deployment)."""
    
    DEBUG = False
    TESTING = False
    
    # Production logging
    LOG_LEVEL = 'INFO'
    
    # Enable CSRF protection
    WTF_CSRF_ENABLED = True
    
    # Stricter session settings
    SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production-specific settings
    PREFERRED_URL_SCHEME = 'http'  # Change to 'https' if using SSL


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Made with Bob
