"""
Favorite Routes Model.

Stores user's favorite routes for quick access.
"""

from datetime import datetime
from .base import db, Base


class FavoriteRoute(Base):
    """
    User's favorite routes.
    
    Stores route IDs that users have marked as favorites
    for quick access and filtering.
    """
    __tablename__ = 'favorite_routes'
    
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    route_type = db.Column(db.String(20), nullable=False)  # 'commute' or 'long_ride'
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<FavoriteRoute {self.route_id} ({self.route_type})>'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'route_id': self.route_id,
            'route_type': self.route_type,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'notes': self.notes
        }

# Made with Bob