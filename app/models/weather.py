"""
Weather model for storing weather snapshots.

Stores current and forecast weather data with comfort scoring for cycling.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.models.base import db, TimestampMixin


class WeatherSnapshot(db.Model, TimestampMixin):
    """
    Weather snapshot with comfort scoring for cycling.
    
    Stores weather data with calculated comfort metrics to help
    users make informed decisions about cycling conditions.
    """
    __tablename__ = 'weather_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Location
    latitude = db.Column(db.Float, nullable=False, index=True)
    longitude = db.Column(db.Float, nullable=False, index=True)
    location_name = db.Column(db.String(200))
    
    # Timestamp
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Weather data
    temperature_c = db.Column(db.Float)
    conditions = db.Column(db.String(100))
    wind_speed_kph = db.Column(db.Float)
    wind_direction_deg = db.Column(db.Integer)
    precipitation_mm = db.Column(db.Float)
    humidity_pct = db.Column(db.Float)
    
    # Computed metrics
    comfort_score = db.Column(db.Float)  # 0-1 scale
    cycling_favorability = db.Column(db.String(20))  # favorable, neutral, unfavorable
    
    # Metadata
    is_current = db.Column(db.Boolean, default=True, index=True)
    forecast_time = db.Column(db.DateTime(timezone=True))  # For forecast data
    
    def __repr__(self):
        return f'<WeatherSnapshot {self.location_name} at {self.timestamp}>'
    
    @classmethod
    def get_current_for_location(cls, lat: float, lon: float, 
                                 max_age_hours: int = 2) -> Optional['WeatherSnapshot']:
        """
        Get most recent weather snapshot for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            max_age_hours: Maximum age in hours (default: 2)
            
        Returns:
            WeatherSnapshot if found within max_age, None otherwise
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Find nearest location within 0.01 degrees (~1km)
        return cls.query.filter(
            cls.is_current == True,
            cls.timestamp >= cutoff_time,
            cls.latitude.between(lat - 0.01, lat + 0.01),
            cls.longitude.between(lon - 0.01, lon + 0.01)
        ).order_by(cls.timestamp.desc()).first()
    
    @classmethod
    def create_from_weather_data(cls, weather_data: Dict[str, Any],
                                location_name: Optional[str] = None,
                                is_current: bool = True,
                                forecast_time: Optional[datetime] = None) -> 'WeatherSnapshot':
        """
        Create weather snapshot from weather data dictionary.
        
        Args:
            weather_data: Weather data from fetcher
            location_name: Optional location name
            is_current: Whether this is current weather (vs forecast)
            forecast_time: Forecast time for forecast data
            
        Returns:
            Created WeatherSnapshot
        """
        snapshot = cls(
            latitude=weather_data.get('latitude', 0.0),
            longitude=weather_data.get('longitude', 0.0),
            location_name=location_name,
            temperature_c=weather_data.get('temperature'),
            conditions=weather_data.get('conditions'),
            wind_speed_kph=weather_data.get('wind_speed'),
            wind_direction_deg=weather_data.get('wind_direction'),
            precipitation_mm=weather_data.get('precipitation'),
            humidity_pct=weather_data.get('humidity'),
            is_current=is_current,
            forecast_time=forecast_time
        )
        
        # Calculate comfort metrics
        snapshot._calculate_comfort_metrics()
        
        db.session.add(snapshot)
        db.session.commit()
        
        return snapshot
    
    def _calculate_comfort_metrics(self):
        """Calculate comfort score and cycling favorability."""
        score = 1.0
        
        # Temperature scoring (optimal: 15-25°C / 59-77°F)
        if self.temperature_c is not None:
            if self.temperature_c < 0:  # Below freezing
                score -= 0.4
            elif self.temperature_c < 10:  # Cold
                score -= 0.2
            elif self.temperature_c > 30:  # Hot
                score -= 0.3
            elif self.temperature_c > 25:  # Warm
                score -= 0.1
        
        # Wind scoring (unfavorable above 20 kph / 12 mph)
        if self.wind_speed_kph is not None:
            if self.wind_speed_kph > 30:  # Strong wind
                score -= 0.3
            elif self.wind_speed_kph > 20:  # Moderate wind
                score -= 0.15
        
        # Precipitation scoring
        if self.precipitation_mm is not None and self.precipitation_mm > 0:
            if self.precipitation_mm > 5:  # Heavy rain
                score -= 0.4
            elif self.precipitation_mm > 1:  # Light rain
                score -= 0.3
            else:  # Drizzle
                score -= 0.2
        
        self.comfort_score = max(0.0, min(1.0, score))
        
        # Determine favorability
        if self.comfort_score >= 0.7:
            self.cycling_favorability = 'favorable'
        elif self.comfort_score >= 0.4:
            self.cycling_favorability = 'neutral'
        else:
            self.cycling_favorability = 'unfavorable'
    
    @classmethod
    def cleanup_old_snapshots(cls, days: int = 7) -> int:
        """
        Delete weather snapshots older than specified days.
        
        Args:
            days: Number of days to keep (default: 7)
            
        Returns:
            Number of snapshots deleted
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        deleted = cls.query.filter(cls.timestamp < cutoff_time).delete()
        db.session.commit()
        
        return deleted
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        age_hours = None
        if self.timestamp:
            # Ensure timestamp is timezone-aware for comparison
            ts = self.timestamp if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        
        return {
            'id': self.id,
            'location': {
                'lat': self.latitude,
                'lon': self.longitude,
                'name': self.location_name
            },
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'temperature_c': self.temperature_c,
            'conditions': self.conditions,
            'wind_speed_kph': self.wind_speed_kph,
            'wind_direction_deg': self.wind_direction_deg,
            'precipitation_mm': self.precipitation_mm,
            'humidity_pct': self.humidity_pct,
            'comfort_score': self.comfort_score,
            'cycling_favorability': self.cycling_favorability,
            'is_current': self.is_current,
            'forecast_time': self.forecast_time.isoformat() if self.forecast_time else None,
            'age_hours': age_hours,
            'is_stale': age_hours > 2 if age_hours else False
        }
    
    def save(self):
        """Save changes to database."""
        db.session.add(self)
        db.session.commit()


# Made with Bob
