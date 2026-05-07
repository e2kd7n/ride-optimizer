"""
TrainerRoad Service - Workout integration.

Provides TrainerRoad workout calendar integration via ICS feed parsing.
Supports workout-aware commute recommendations.
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, date, timedelta
from icalendar import Calendar
import requests
from pathlib import Path

from app.models.workouts import WorkoutMetadata
from app.models.base import db
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TrainerRoadService:
    """
    Service for TrainerRoad workout integration.
    
    Fetches workout calendar from TrainerRoad ICS feed and provides
    workout-fit analysis for commute recommendations.
    """
    
    def __init__(self, config=None):
        """
        Initialize TrainerRoad service.
        
        Args:
            config: Optional configuration object
        """
        self.config = config
        self.enabled = False
        self.ics_url = None
        self.encryption_key = None
        
        # Try to load encryption key and ICS URL
        try:
            key_file = Path("config/.trainerroad_encryption_key")
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    self.encryption_key = f.read()
                
                # Try to load encrypted ICS URL
                url_file = Path("config/.trainerroad_ics_url.enc")
                if url_file.exists():
                    with open(url_file, 'rb') as f:
                        encrypted_url = f.read()
                    
                    fernet = Fernet(self.encryption_key)
                    self.ics_url = fernet.decrypt(encrypted_url).decode()
                    self.enabled = True
                    logger.info("TrainerRoad service initialized with encrypted ICS URL")
                else:
                    logger.warning("TrainerRoad ICS URL not configured")
            else:
                logger.warning("TrainerRoad encryption key not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize TrainerRoad service: {e}")
    
    def set_ics_url(self, ics_url: str) -> bool:
        """
        Set and encrypt the TrainerRoad ICS URL.
        
        Args:
            ics_url: TrainerRoad calendar ICS URL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate encryption key if not exists
            if self.encryption_key is None:
                self.encryption_key = Fernet.generate_key()
                key_file = Path("config/.trainerroad_encryption_key")
                key_file.parent.mkdir(parents=True, exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(self.encryption_key)
                logger.info("Generated new encryption key")
            
            # Encrypt and save ICS URL
            fernet = Fernet(self.encryption_key)
            encrypted_url = fernet.encrypt(ics_url.encode())
            
            url_file = Path("config/.trainerroad_ics_url.enc")
            with open(url_file, 'wb') as f:
                f.write(encrypted_url)
            
            self.ics_url = ics_url
            self.enabled = True
            logger.info("TrainerRoad ICS URL configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set ICS URL: {e}")
            return False
    
    def sync_workouts(self, days_ahead: int = 14) -> Dict[str, Any]:
        """
        Sync workouts from TrainerRoad ICS feed.
        
        Args:
            days_ahead: Number of days to sync ahead
            
        Returns:
            Dictionary with sync results
        """
        if not self.enabled or not self.ics_url:
            return {
                'status': 'error',
                'message': 'TrainerRoad not configured'
            }
        
        try:
            # Fetch ICS feed
            response = requests.get(self.ics_url, timeout=10)
            response.raise_for_status()
            
            # Parse calendar
            cal = Calendar.from_ical(response.content)
            
            # Extract workouts
            workouts_added = 0
            workouts_updated = 0
            start_date = date.today()
            end_date = start_date + timedelta(days=days_ahead)
            
            for component in cal.walk('VEVENT'):
                try:
                    # Extract workout details
                    workout_date = component.get('dtstart').dt
                    if isinstance(workout_date, datetime):
                        workout_date = workout_date.date()
                    
                    # Skip if outside date range
                    if workout_date < start_date or workout_date > end_date:
                        continue
                    
                    workout_id = str(component.get('uid'))
                    workout_name = str(component.get('summary', 'Unnamed Workout'))
                    description = str(component.get('description', ''))
                    
                    # Parse workout type and details from description
                    workout_type, duration, tss, intensity = self._parse_workout_details(
                        workout_name, description
                    )
                    
                    # Check if workout exists
                    existing = WorkoutMetadata.query.filter_by(workout_id=workout_id).first()
                    
                    if existing:
                        # Update existing workout
                        existing.workout_name = workout_name
                        existing.workout_date = workout_date
                        existing.workout_type = workout_type
                        existing.duration_minutes = duration
                        existing.tss = tss
                        existing.intensity_factor = intensity
                        existing.synced_at = datetime.utcnow()
                        workouts_updated += 1
                    else:
                        # Create new workout
                        workout = WorkoutMetadata(
                            workout_id=workout_id,
                            workout_name=workout_name,
                            workout_date=workout_date,
                            workout_type=workout_type,
                            duration_minutes=duration,
                            tss=tss,
                            intensity_factor=intensity,
                            status='scheduled',
                            synced_at=datetime.utcnow()
                        )
                        db.session.add(workout)
                        workouts_added += 1
                
                except Exception as e:
                    logger.warning(f"Error parsing workout event: {e}")
                    continue
            
            # Commit changes
            db.session.commit()
            
            logger.info(f"Synced TrainerRoad workouts: {workouts_added} added, {workouts_updated} updated")
            
            return {
                'status': 'success',
                'workouts_added': workouts_added,
                'workouts_updated': workouts_updated,
                'total': workouts_added + workouts_updated
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching TrainerRoad ICS feed: {e}")
            return {
                'status': 'error',
                'message': f'Failed to fetch ICS feed: {str(e)}'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing workouts: {e}")
            return {
                'status': 'error',
                'message': f'Sync failed: {str(e)}'
            }
    
    def get_workout_for_date(self, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Get workout scheduled for a specific date.
        
        Args:
            target_date: Date to query
            
        Returns:
            Workout dictionary or None
        """
        workout = WorkoutMetadata.get_for_date(target_date)
        return workout.to_dict() if workout else None
    
    def get_upcoming_workouts(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get upcoming scheduled workouts.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of workout dictionaries
        """
        workouts = WorkoutMetadata.get_upcoming(days)
        return [w.to_dict() for w in workouts]
    
    def calculate_workout_fit(self, route_distance_m: float, route_duration_s: float,
                             workout: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Calculate how well a route fits a workout.
        
        Args:
            route_distance_m: Route distance in meters
            route_duration_s: Route duration in seconds
            workout: Optional workout dictionary (uses today's workout if None)
            
        Returns:
            Fit analysis dictionary
        """
        # Get workout if not provided
        if workout is None:
            workout = self.get_workout_for_date(date.today())
        
        if not workout:
            return {
                'status': 'no_workout',
                'fit_score': 0.0,
                'reason': 'No workout scheduled for today'
            }
        
        # Convert route metrics
        route_duration_min = route_duration_s / 60
        route_distance_km = route_distance_m / 1000
        
        # Get workout details
        workout_duration = workout.get('duration_minutes', 60)
        workout_type = workout.get('workout_type', 'Endurance')
        workout_tss = workout.get('tss', 50)
        workout_intensity = workout.get('intensity_factor', 0.7)
        
        # Calculate fit components
        duration_fit = self._calculate_duration_fit(route_duration_min, workout_duration)
        intensity_fit = self._calculate_intensity_fit(route_distance_km, route_duration_min, 
                                                      workout_type, workout_intensity)
        type_fit = self._calculate_type_fit(workout_type)
        
        # Weighted average (duration 40%, intensity 30%, type 20%, variety 10%)
        fit_score = (duration_fit * 0.4 + intensity_fit * 0.3 + 
                    type_fit * 0.2 + 0.1)  # 0.1 for variety bonus
        
        # Generate reason
        reason = self._generate_fit_reason(duration_fit, intensity_fit, type_fit, 
                                          workout_type, workout_duration)
        
        return {
            'status': 'success',
            'fit_score': round(fit_score, 2),
            'reason': reason,
            'workout_name': workout.get('workout_name'),
            'workout_type': workout_type,
            'duration_match': duration_fit > 0.7,
            'intensity_match': intensity_fit > 0.7
        }
    
    @staticmethod
    def _parse_workout_details(name: str, description: str) -> tuple:
        """
        Parse workout type and details from name/description.
        
        Returns:
            Tuple of (type, duration_minutes, tss, intensity_factor)
        """
        # Default values
        workout_type = 'Endurance'
        duration = 60
        tss = 50
        intensity = 0.7
        
        # Parse workout type from name
        name_lower = name.lower()
        if 'threshold' in name_lower or 'sweet spot' in name_lower:
            workout_type = 'Threshold'
            intensity = 0.9
            tss = 70
        elif 'vo2' in name_lower or 'vo2max' in name_lower:
            workout_type = 'VO2Max'
            intensity = 1.05
            tss = 80
        elif 'recovery' in name_lower or 'easy' in name_lower:
            workout_type = 'Recovery'
            intensity = 0.55
            tss = 30
        elif 'endurance' in name_lower:
            workout_type = 'Endurance'
            intensity = 0.7
            tss = 50
        
        # Try to parse duration from description (common format: "60 min")
        import re
        duration_match = re.search(r'(\d+)\s*min', description.lower())
        if duration_match:
            duration = int(duration_match.group(1))
        
        # Try to parse TSS
        tss_match = re.search(r'tss[:\s]*(\d+)', description.lower())
        if tss_match:
            tss = int(tss_match.group(1))
        
        return workout_type, duration, tss, intensity
    
    @staticmethod
    def _calculate_duration_fit(route_duration: float, workout_duration: float) -> float:
        """Calculate duration fit score (0-1)."""
        if workout_duration == 0:
            return 0.5
        
        ratio = route_duration / workout_duration
        
        # Perfect match at 0.8-1.2x workout duration
        if 0.8 <= ratio <= 1.2:
            return 1.0
        elif 0.6 <= ratio <= 1.5:
            return 0.8
        elif 0.4 <= ratio <= 2.0:
            return 0.6
        else:
            return 0.3
    
    @staticmethod
    def _calculate_intensity_fit(distance_km: float, duration_min: float,
                                 workout_type: str, intensity_factor: float) -> float:
        """Calculate intensity fit score (0-1)."""
        if duration_min == 0:
            return 0.5
        
        # Calculate average speed (km/h)
        avg_speed = (distance_km / duration_min) * 60
        
        # Expected speeds for different workout types (cycling)
        type_speeds = {
            'Recovery': 20,
            'Endurance': 25,
            'Threshold': 30,
            'VO2Max': 32
        }
        
        expected_speed = type_speeds.get(workout_type, 25)
        speed_ratio = avg_speed / expected_speed
        
        # Score based on how close to expected
        if 0.9 <= speed_ratio <= 1.1:
            return 1.0
        elif 0.8 <= speed_ratio <= 1.2:
            return 0.8
        elif 0.7 <= speed_ratio <= 1.3:
            return 0.6
        else:
            return 0.4
    
    @staticmethod
    def _calculate_type_fit(workout_type: str) -> float:
        """Calculate type fit score (0-1)."""
        # Commutes are generally good for Endurance and Threshold
        type_scores = {
            'Endurance': 1.0,
            'Threshold': 0.9,
            'Recovery': 0.7,
            'VO2Max': 0.6
        }
        return type_scores.get(workout_type, 0.8)
    
    @staticmethod
    def _generate_fit_reason(duration_fit: float, intensity_fit: float, 
                            type_fit: float, workout_type: str, 
                            workout_duration: int) -> str:
        """Generate human-readable fit reason."""
        reasons = []
        
        if duration_fit >= 0.8:
            reasons.append(f"Good duration match for {workout_duration}min workout")
        elif duration_fit >= 0.6:
            reasons.append(f"Acceptable duration for {workout_duration}min workout")
        else:
            reasons.append(f"Duration mismatch with {workout_duration}min workout")
        
        if intensity_fit >= 0.8:
            reasons.append(f"Intensity matches {workout_type} workout")
        elif intensity_fit >= 0.6:
            reasons.append(f"Moderate intensity for {workout_type}")
        else:
            reasons.append(f"Intensity doesn't match {workout_type}")
        
        if type_fit >= 0.9:
            reasons.append("Excellent workout type for commuting")
        elif type_fit >= 0.7:
            reasons.append("Good workout type for commuting")
        
        return "; ".join(reasons)


# Made with Bob