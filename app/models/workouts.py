"""
Workout metadata model for TrainerRoad integration.

Stores workout information and fit analysis results.
"""

from datetime import datetime
from .base import db, TimestampMixin


class WorkoutMetadata(db.Model, TimestampMixin):
    """
    TrainerRoad workout metadata and fit analysis.
    
    Stores workout information to support workout-fit recommendations
    without re-fetching from TrainerRoad API on every request.
    """
    __tablename__ = 'workout_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Workout identification
    workout_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    workout_name = db.Column(db.String(200), nullable=False)
    workout_date = db.Column(db.Date, nullable=False, index=True)
    
    # Workout details
    workout_type = db.Column(db.String(50), nullable=True)  # 'Endurance', 'Threshold', 'VO2Max', etc.
    duration_minutes = db.Column(db.Integer, nullable=True)
    tss = db.Column(db.Float, nullable=True)  # Training Stress Score
    intensity_factor = db.Column(db.Float, nullable=True)
    
    # Workout status
    status = db.Column(db.String(20), nullable=False, default='scheduled')  # 'scheduled', 'completed', 'skipped'
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Fit analysis
    fit_score = db.Column(db.Float, nullable=True)  # 0-1, how well commute fits workout
    fit_reason = db.Column(db.Text, nullable=True)  # Explanation of fit score
    recommended_route_id = db.Column(db.String(100), nullable=True)  # Best route for this workout
    
    # Metadata
    notes = db.Column(db.Text, nullable=True)
    synced_at = db.Column(db.DateTime, nullable=True)  # Last sync from TrainerRoad
    
    def __repr__(self):
        return f'<WorkoutMetadata {self.workout_id} {self.workout_name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'workout_id': self.workout_id,
            'workout_name': self.workout_name,
            'workout_date': self.workout_date.isoformat() if self.workout_date else None,
            'workout_type': self.workout_type,
            'duration_minutes': self.duration_minutes,
            'tss': self.tss,
            'intensity_factor': self.intensity_factor,
            'status': self.status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'fit_score': self.fit_score,
            'fit_reason': self.fit_reason,
            'recommended_route_id': self.recommended_route_id,
            'notes': self.notes,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_upcoming(cls, days=7):
        """
        Get upcoming scheduled workouts.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of WorkoutMetadata instances
        """
        from datetime import date, timedelta
        
        start_date = date.today()
        end_date = start_date + timedelta(days=days)
        
        return cls.query.filter(
            cls.workout_date >= start_date,
            cls.workout_date <= end_date,
            cls.status == 'scheduled'
        ).order_by(cls.workout_date).all()
    
    @classmethod
    def get_for_date(cls, target_date):
        """
        Get workout for a specific date.
        
        Args:
            target_date: Date to query
            
        Returns:
            WorkoutMetadata instance or None
        """
        return cls.query.filter_by(workout_date=target_date).first()
    
    @classmethod
    def sync_from_trainerroad(cls, workouts_data):
        """
        Sync workouts from TrainerRoad API response.
        
        Args:
            workouts_data: List of workout dictionaries from TrainerRoad API
            
        Returns:
            Number of workouts synced
        """
        count = 0
        sync_time = datetime.utcnow()
        
        for workout_data in workouts_data:
            workout_id = workout_data.get('id')
            if not workout_id:
                continue
            
            workout = cls.query.filter_by(workout_id=str(workout_id)).first()
            
            if workout:
                # Update existing
                workout.workout_name = workout_data.get('name', workout.workout_name)
                workout.workout_type = workout_data.get('type')
                workout.duration_minutes = workout_data.get('duration')
                workout.tss = workout_data.get('tss')
                workout.intensity_factor = workout_data.get('if')
                workout.synced_at = sync_time
            else:
                # Create new
                workout = cls(
                    workout_id=str(workout_id),
                    workout_name=workout_data.get('name', 'Unknown Workout'),
                    workout_date=workout_data.get('date'),
                    workout_type=workout_data.get('type'),
                    duration_minutes=workout_data.get('duration'),
                    tss=workout_data.get('tss'),
                    intensity_factor=workout_data.get('if'),
                    synced_at=sync_time
                )
                db.session.add(workout)
            
            count += 1
        
        db.session.commit()
        return count
    
    def calculate_fit(self, route_groups):
        """
        Calculate workout fit for available routes.
        
        Args:
            route_groups: List of RouteGroup objects
            
        Returns:
            Best fit route and score
        """
        # TODO: Implement workout fit algorithm
        # For now, return placeholder
        if not route_groups:
            return None, 0.0
        
        # Simple heuristic: match workout type to route characteristics
        best_route = None
        best_score = 0.0
        
        for group in route_groups:
            score = 0.5  # Base score
            
            # Adjust based on workout type
            if self.workout_type == 'Endurance':
                # Prefer longer, flatter routes
                if group.avg_distance > 15000:  # > 15km
                    score += 0.2
                if group.avg_elevation < 200:  # < 200m
                    score += 0.2
            elif self.workout_type in ['Threshold', 'VO2Max']:
                # Prefer routes with some elevation
                if group.avg_elevation > 200:
                    score += 0.3
            
            if score > best_score:
                best_score = score
                best_route = group
        
        if best_route:
            self.fit_score = best_score
            self.recommended_route_id = best_route.group_id
            self.fit_reason = f"Good match for {self.workout_type} workout"
            db.session.commit()
        
        return best_route, best_score

# Made with Bob
