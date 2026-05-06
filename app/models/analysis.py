"""
Analysis snapshot models.

Stores metadata about analysis runs and their results.
Heavy data (coordinates, full activity details) stays in file caches.
"""

from datetime import datetime
from .base import db, TimestampMixin


class AnalysisSnapshot(db.Model, TimestampMixin):
    """
    Snapshot of an analysis run.
    
    Stores high-level metadata about analysis results to support
    dashboard rendering without re-running full analysis.
    
    Heavy artifacts (route coordinates, activity details) remain in file caches.
    This table stores just enough to render summaries and check freshness.
    """
    __tablename__ = 'analysis_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Analysis metadata
    analysis_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'error', 'in_progress'
    error_message = db.Column(db.Text, nullable=True)
    
    # Data counts
    activities_count = db.Column(db.Integer, nullable=False, default=0)
    route_groups_count = db.Column(db.Integer, nullable=False, default=0)
    long_rides_count = db.Column(db.Integer, nullable=False, default=0)
    
    # Location info (for quick access)
    home_lat = db.Column(db.Float, nullable=True)
    home_lon = db.Column(db.Float, nullable=True)
    home_name = db.Column(db.String(200), nullable=True)
    work_lat = db.Column(db.Float, nullable=True)
    work_lon = db.Column(db.Float, nullable=True)
    work_name = db.Column(db.String(200), nullable=True)
    
    # Data freshness indicators
    strava_last_sync = db.Column(db.DateTime, nullable=True)
    weather_last_sync = db.Column(db.DateTime, nullable=True)
    geocoding_complete = db.Column(db.Boolean, nullable=False, default=False)
    
    # Performance metrics
    analysis_duration_seconds = db.Column(db.Float, nullable=True)
    
    # Relationships
    route_groups = db.relationship('RouteGroup', back_populates='snapshot', cascade='all, delete-orphan')
    long_rides = db.relationship('LongRide', back_populates='snapshot', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AnalysisSnapshot {self.id} {self.analysis_date} {self.status}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'status': self.status,
            'error_message': self.error_message,
            'activities_count': self.activities_count,
            'route_groups_count': self.route_groups_count,
            'long_rides_count': self.long_rides_count,
            'home_location': {
                'lat': self.home_lat,
                'lon': self.home_lon,
                'name': self.home_name
            } if self.home_lat else None,
            'work_location': {
                'lat': self.work_lat,
                'lon': self.work_lon,
                'name': self.work_name
            } if self.work_lat else None,
            'strava_last_sync': self.strava_last_sync.isoformat() if self.strava_last_sync else None,
            'weather_last_sync': self.weather_last_sync.isoformat() if self.weather_last_sync else None,
            'geocoding_complete': self.geocoding_complete,
            'analysis_duration_seconds': self.analysis_duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_latest(cls):
        """Get the most recent successful analysis snapshot."""
        return cls.query.filter_by(status='success').order_by(cls.analysis_date.desc()).first()
    
    @classmethod
    def is_stale(cls, hours=24):
        """
        Check if latest analysis is stale.
        
        Args:
            hours: Number of hours after which data is considered stale
            
        Returns:
            True if no recent analysis or latest is older than threshold
        """
        latest = cls.get_latest()
        if not latest:
            return True
        
        age = datetime.utcnow() - latest.analysis_date
        return age.total_seconds() > (hours * 3600)

# Made with Bob
