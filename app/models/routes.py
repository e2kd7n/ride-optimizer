"""
Route models for commute groups and long rides.

Stores summary information about routes.
Full coordinates and detailed data remain in file caches.
"""

from .base import db, TimestampMixin


class RouteGroup(db.Model, TimestampMixin):
    """
    Summary of a commute route group.
    
    Stores high-level information about route groups for quick access.
    Full route coordinates and detailed metrics remain in file caches.
    """
    __tablename__ = 'route_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to analysis snapshot
    snapshot_id = db.Column(db.Integer, db.ForeignKey('analysis_snapshots.id'), nullable=False, index=True)
    snapshot = db.relationship('AnalysisSnapshot', back_populates='route_groups')
    
    # Route identification
    group_id = db.Column(db.String(100), nullable=False, index=True)  # e.g., "home_to_work_1"
    name = db.Column(db.String(200), nullable=True)  # Human-readable name
    direction = db.Column(db.String(20), nullable=False)  # "home_to_work" or "work_to_home"
    
    # Summary statistics
    frequency = db.Column(db.Integer, nullable=False, default=0)  # Number of times used
    avg_distance = db.Column(db.Float, nullable=False)  # meters
    avg_duration = db.Column(db.Float, nullable=False)  # seconds
    avg_elevation = db.Column(db.Float, nullable=False)  # meters
    avg_speed = db.Column(db.Float, nullable=False)  # m/s
    
    # Route characteristics
    is_plus_route = db.Column(db.Boolean, nullable=False, default=False)
    consistency_score = db.Column(db.Float, nullable=True)  # 0-1
    
    # User preferences
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<RouteGroup {self.group_id} {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'name': self.name,
            'direction': self.direction,
            'frequency': self.frequency,
            'avg_distance': self.avg_distance,
            'avg_duration': self.avg_duration,
            'avg_elevation': self.avg_elevation,
            'avg_speed': self.avg_speed,
            'is_plus_route': self.is_plus_route,
            'consistency_score': self.consistency_score,
            'is_favorite': self.is_favorite,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LongRide(db.Model, TimestampMixin):
    """
    Summary of a long/recreational ride.
    
    Stores high-level information about long rides for quick access.
    Full route coordinates remain in file caches.
    """
    __tablename__ = 'long_rides'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to analysis snapshot
    snapshot_id = db.Column(db.Integer, db.ForeignKey('analysis_snapshots.id'), nullable=False, index=True)
    snapshot = db.relationship('AnalysisSnapshot', back_populates='long_rides')
    
    # Ride identification
    activity_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    ride_type = db.Column(db.String(50), nullable=True)  # 'Ride', 'GravelRide', etc.
    
    # Summary statistics
    distance = db.Column(db.Float, nullable=False)  # meters
    duration = db.Column(db.Integer, nullable=False)  # seconds
    elevation_gain = db.Column(db.Float, nullable=False)  # meters
    average_speed = db.Column(db.Float, nullable=False)  # m/s
    
    # Location info
    start_lat = db.Column(db.Float, nullable=True)
    start_lon = db.Column(db.Float, nullable=True)
    end_lat = db.Column(db.Float, nullable=True)
    end_lon = db.Column(db.Float, nullable=True)
    is_loop = db.Column(db.Boolean, nullable=False, default=False)
    
    # Usage tracking
    uses = db.Column(db.Integer, nullable=False, default=1)  # Number of times ridden
    last_ridden = db.Column(db.DateTime, nullable=True)
    
    # User preferences
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    
    def __repr__(self):
        return f'<LongRide {self.activity_id} {self.name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'activity_id': self.activity_id,
            'name': self.name,
            'ride_type': self.ride_type,
            'distance': self.distance,
            'duration': self.duration,
            'elevation_gain': self.elevation_gain,
            'average_speed': self.average_speed,
            'start_location': {
                'lat': self.start_lat,
                'lon': self.start_lon
            } if self.start_lat else None,
            'end_location': {
                'lat': self.end_lat,
                'lon': self.end_lon
            } if self.end_lat else None,
            'is_loop': self.is_loop,
            'uses': self.uses,
            'last_ridden': self.last_ridden.isoformat() if self.last_ridden else None,
            'is_favorite': self.is_favorite,
            'notes': self.notes,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Made with Bob
