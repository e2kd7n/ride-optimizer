"""
Weather model - STUB for testing until Issue #138 is complete.

This is a temporary stub to allow testing of other modules.
Will be replaced with full implementation when weather integration is complete.
"""

from datetime import datetime
from typing import Optional
from app.models.base import db


class WeatherSnapshot(db.Model):
    """
    STUB: Weather snapshot model.
    
    This is a minimal stub to unblock testing.
    Full implementation pending Issue #138 (Weather Integration).
    """
    __tablename__ = 'weather_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    location_lat = db.Column(db.Float, nullable=False)
    location_lon = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    temperature = db.Column(db.Float)
    conditions = db.Column(db.String(100))
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.String(10))
    precipitation = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WeatherSnapshot {self.id} at {self.timestamp}>'
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'location': {'lat': self.location_lat, 'lon': self.location_lon},
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'temperature': self.temperature,
            'conditions': self.conditions,
            'wind_speed': self.wind_speed,
            'wind_direction': self.wind_direction,
            'precipitation': self.precipitation
        }

# Made with Bob
