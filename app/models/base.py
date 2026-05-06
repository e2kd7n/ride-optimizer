"""
Base database configuration and utilities.

Provides SQLAlchemy setup and base model class.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Define naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all database models."""
    metadata = metadata


# Initialize SQLAlchemy with custom base
db = SQLAlchemy(model_class=Base)


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db(app):
    """
    Initialize database with Flask app.
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Log initialization
        app.logger.info(f"Database initialized: {app.config['SQLALCHEMY_DATABASE_URI']}")


def reset_db(app):
    """
    Drop and recreate all tables.
    
    WARNING: This will delete all data!
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        app.logger.warning("Database reset complete - all data deleted")

# Made with Bob
