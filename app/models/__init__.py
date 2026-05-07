"""
Database models for Ride Optimizer web platform.

This module defines SQLAlchemy models for structured data persistence.
Heavy artifacts (route coordinates, activity data) remain in file caches.

Models:
- AnalysisSnapshot: Cached analysis results and metadata
- RouteGroup: Commute route group summaries
- LongRide: Long ride summaries
- UserPreference: User settings and preferences
- JobHistory: Background job execution history
- WorkoutMetadata: TrainerRoad workout information
- WeatherSnapshot: Weather data with comfort scoring
"""

from .base import Base, db
from .analysis import AnalysisSnapshot
from .routes import RouteGroup, LongRide
from .preferences import UserPreference
from .jobs import JobHistory
from .workouts import WorkoutMetadata
from .weather import WeatherSnapshot

__all__ = [
    'Base',
    'db',
    'AnalysisSnapshot',
    'RouteGroup',
    'LongRide',
    'UserPreference',
    'JobHistory',
    'WorkoutMetadata',
    'WeatherSnapshot',
]

# Made with Bob
