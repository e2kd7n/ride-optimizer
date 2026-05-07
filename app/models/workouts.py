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
        
        Scoring algorithm considers:
        - Duration match (workout duration vs route duration)
        - TSS/intensity match (workout intensity vs route elevation)
        - Workout type characteristics
        - Route variety and freshness
        
        Args:
            route_groups: List of RouteGroup objects
            
        Returns:
            Best fit route and score (0.0-1.0)
        """
        if not route_groups:
            return None, 0.0
        
        best_route = None
        best_score = 0.0
        best_reason = ""
        
        # Target duration in hours (convert from minutes)
        target_duration_hours = self.duration_minutes / 60.0
        
        for group in route_groups:
            score = 0.0
            reasons = []
            
            # 1. Duration match (40% weight)
            # Assume average speed of 15 mph for commute routes
            route_duration_hours = (group.avg_distance / 1000) / 24.14  # km to hours at 15mph
            duration_diff = abs(route_duration_hours - target_duration_hours)
            
            if duration_diff < 0.25:  # Within 15 minutes
                duration_score = 0.4
                reasons.append("perfect duration match")
            elif duration_diff < 0.5:  # Within 30 minutes
                duration_score = 0.3
                reasons.append("good duration match")
            elif duration_diff < 1.0:  # Within 1 hour
                duration_score = 0.2
                reasons.append("acceptable duration")
            else:
                duration_score = 0.1
                reasons.append("duration mismatch")
            
            score += duration_score
            
            # 2. Intensity/TSS match (30% weight)
            # Higher TSS workouts benefit from hillier routes
            if self.tss:
                if self.tss > 100:  # High intensity
                    if group.avg_elevation > 300:
                        score += 0.3
                        reasons.append("challenging elevation for high TSS")
                    elif group.avg_elevation > 150:
                        score += 0.2
                        reasons.append("moderate elevation")
                    else:
                        score += 0.1
                elif self.tss > 50:  # Moderate intensity
                    if 100 < group.avg_elevation < 300:
                        score += 0.3
                        reasons.append("ideal elevation for moderate TSS")
                    else:
                        score += 0.2
                else:  # Low intensity/recovery
                    if group.avg_elevation < 150:
                        score += 0.3
                        reasons.append("flat route for recovery")
                    else:
                        score += 0.15
            else:
                score += 0.15  # No TSS data, neutral score
            
            # 3. Workout type characteristics (20% weight)
            if self.workout_type == 'Endurance':
                # Prefer longer, steadier routes
                if group.avg_distance > 15000:  # > 15km
                    score += 0.15
                    reasons.append("good endurance distance")
                if group.avg_elevation < 250:
                    score += 0.05
                    reasons.append("steady terrain")
            elif self.workout_type in ['Threshold', 'Sweet Spot']:
                # Prefer routes with sustained climbs
                if 200 < group.avg_elevation < 400:
                    score += 0.2
                    reasons.append("ideal for threshold work")
            elif self.workout_type == 'VO2Max':
                # Prefer routes with punchy climbs
                if group.avg_elevation > 250:
                    score += 0.2
                    reasons.append("good for VO2Max intervals")
            elif self.workout_type == 'Recovery':
                # Prefer flat, easy routes
                if group.avg_elevation < 100:
                    score += 0.15
                    reasons.append("easy recovery terrain")
                if group.avg_distance < 12000:  # < 12km
                    score += 0.05
                    reasons.append("short recovery distance")
            else:
                score += 0.1  # Unknown type, neutral score
            
            # 4. Route variety bonus (10% weight)
            # Prefer routes that haven't been used recently
            if hasattr(group, 'last_used_days') and group.last_used_days:
                if group.last_used_days > 30:
                    score += 0.1
                    reasons.append("fresh route")
                elif group.last_used_days > 14:
                    score += 0.07
                    reasons.append("not recently used")
                elif group.last_used_days > 7:
                    score += 0.05
                else:
                    score += 0.02
            else:
                score += 0.05  # No usage data, neutral score
            
            # Track best route
            if score > best_score:
                best_score = score
                best_route = group
                best_reason = ", ".join(reasons)
        
        # Save fit results
        if best_route:
            self.fit_score = min(best_score, 1.0)  # Cap at 1.0
            self.recommended_route_id = best_route.group_id
            self.fit_reason = f"{self.workout_type} workout: {best_reason}"
            db.session.commit()
        
        return best_route, min(best_score, 1.0)

# Made with Bob
