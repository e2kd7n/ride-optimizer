"""
User preferences model.

Stores user settings and configuration.
"""

from .base import db, TimestampMixin


class UserPreference(db.Model, TimestampMixin):
    """
    User preferences and settings.
    
    Stores configuration for weather thresholds, route preferences,
    notification settings, and other user-specific options.
    """
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Preference category and key
    category = db.Column(db.String(50), nullable=False, index=True)  # 'weather', 'routes', 'notifications', etc.
    key = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)  # JSON-encoded value
    
    # Metadata
    description = db.Column(db.String(500), nullable=True)
    
    # Unique constraint on category + key
    __table_args__ = (
        db.UniqueConstraint('category', 'key', name='uq_preference_category_key'),
    )
    
    def __repr__(self):
        return f'<UserPreference {self.category}.{self.key}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json
        return {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': json.loads(self.value) if self.value else None,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get(cls, category, key, default=None):
        """
        Get a preference value.
        
        Args:
            category: Preference category
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value (parsed from JSON) or default
        """
        import json
        pref = cls.query.filter_by(category=category, key=key).first()
        if pref:
            return json.loads(pref.value)
        return default
    
    @classmethod
    def set(cls, category, key, value, description=None):
        """
        Set a preference value.
        
        Args:
            category: Preference category
            key: Preference key
            value: Value to store (will be JSON-encoded)
            description: Optional description
            
        Returns:
            UserPreference instance
        """
        import json
        pref = cls.query.filter_by(category=category, key=key).first()
        
        if pref:
            pref.value = json.dumps(value)
            if description:
                pref.description = description
        else:
            pref = cls(
                category=category,
                key=key,
                value=json.dumps(value),
                description=description
            )
            db.session.add(pref)
        
        db.session.commit()
        return pref
    
    @classmethod
    def get_category(cls, category):
        """
        Get all preferences in a category.
        
        Args:
            category: Preference category
            
        Returns:
            Dictionary of key: value pairs
        """
        import json
        prefs = cls.query.filter_by(category=category).all()
        return {pref.key: json.loads(pref.value) for pref in prefs}
    
    @classmethod
    def set_defaults(cls):
        """Set default preferences if they don't exist."""
        defaults = {
            'weather': {
                'temperature_unit': 'F',
                'wind_speed_unit': 'mph',
                'max_wind_speed': 20,
                'max_precipitation': 0.1,
                'min_temperature': 40,
                'max_temperature': 95
            },
            'routes': {
                'commute_min_distance': 10,
                'commute_max_distance': 25,
                'long_ride_min_distance': 30,
                'long_ride_max_distance': 100,
                'prefer_variety': True
            },
            'notifications': {
                'email_enabled': False,
                'new_commute_recommendation': True,
                'new_long_ride_recommendation': True,
                'data_sync_complete': False,
                'data_sync_error': True
            },
            'analysis': {
                'auto_sync_interval': 3600,  # seconds
                'cache_ttl': 86400,  # 24 hours
                'enable_weather': True,
                'enable_geocoding': True
            }
        }
        
        for category, prefs in defaults.items():
            for key, value in prefs.items():
                existing = cls.query.filter_by(category=category, key=key).first()
                if not existing:
                    cls.set(category, key, value)

# Made with Bob
