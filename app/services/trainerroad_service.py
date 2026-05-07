"""
TrainerRoad Service - ICS feed ingestion and workout normalization.

Provides:
- ICS feed parsing from TrainerRoad calendar
- Workout metadata extraction
- Normalization to internal planning constraints
- Graceful error handling for feed failures
- Secure storage of ICS feed URL
"""

import logging
import requests
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from icalendar import Calendar, Event
from urllib.parse import urlparse
from cryptography.fernet import Fernet

from src.config import Config
from app.models.workouts import WorkoutMetadata
from app.models.base import db

logger = logging.getLogger(__name__)


class TrainerRoadService:
    """
    Service for TrainerRoad ICS feed integration.
    
    Features:
    - Parse ICS calendar feeds
    - Extract workout metadata (name, date, duration, type)
    - Normalize to internal planning constraints
    - Store in WorkoutMetadata model
    - Handle stale/missing/invalid feeds gracefully
    - Secure encrypted storage of ICS feed URL
    """
    
    def __init__(self, config: Config):
        """
        Initialize TrainerRoad service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.credentials_path = Path('config/trainerroad_credentials.json')
        self.key_file = Path('config/.trainerroad_encryption_key')
        self.last_sync = None
        self.sync_interval_hours = 6  # Re-sync every 6 hours
        
        # Initialize encryption
        self.cipher = self._get_cipher()
        
        # Load feed URL from secure storage
        self.feed_url = self._load_feed_url()
    
    def _get_cipher(self) -> Fernet:
        """
        Get or create Fernet cipher for encryption.
        
        Returns:
            Fernet cipher instance
        """
        # Check environment variable first
        env_key = os.getenv('TRAINERROAD_ENCRYPTION_KEY')
        if env_key:
            return Fernet(env_key.encode())
        
        # Check for existing key file
        if self.key_file.exists():
            try:
                key = self.key_file.read_bytes()
                return Fernet(key)
            except Exception as e:
                logger.warning(f"Failed to load encryption key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        
        try:
            # Create directory with restrictive permissions
            self.key_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            
            # Write key with secure permissions
            self.key_file.write_bytes(key)
            os.chmod(self.key_file, 0o600)
            
            logger.info(f"Generated new TrainerRoad encryption key: {self.key_file}")
        except Exception as e:
            logger.error(f"Failed to save encryption key: {e}")
        
        return Fernet(key)
    
    def _load_feed_url(self) -> Optional[str]:
        """
        Load ICS feed URL from encrypted storage.
        
        Returns:
            Feed URL or None if not configured
        """
        if not self.credentials_path.exists():
            return None
        
        try:
            with open(self.credentials_path, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self.cipher.decrypt(encrypted)
            data = json.loads(decrypted.decode())
            
            feed_url = data.get('ics_feed_url')
            if feed_url:
                logger.info("Loaded TrainerRoad ICS feed URL from secure storage")
            return feed_url
            
        except Exception as e:
            logger.error(f"Failed to load TrainerRoad credentials: {e}")
            return None
    
    def _save_feed_url(self, feed_url: str) -> bool:
        """
        Save ICS feed URL to encrypted storage.
        
        Args:
            feed_url: ICS calendar feed URL
            
        Returns:
            True if saved successfully
        """
        try:
            # Create directory with restrictive permissions
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            
            # Encrypt data
            data = {'ics_feed_url': feed_url}
            data_json = json.dumps(data)
            encrypted = self.cipher.encrypt(data_json.encode())
            
            # Write encrypted data
            with open(self.credentials_path, 'wb') as f:
                f.write(encrypted)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.credentials_path, 0o600)
            
            logger.info(f"Saved TrainerRoad ICS feed URL securely to {self.credentials_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save TrainerRoad credentials: {e}")
            return False
    
    def set_feed_url(self, feed_url: str) -> bool:
        """
        Set and validate TrainerRoad ICS feed URL with secure storage.
        
        Args:
            feed_url: ICS calendar feed URL
            
        Returns:
            True if URL is valid and saved, False otherwise
        """
        try:
            parsed = urlparse(feed_url)
            if not all([parsed.scheme, parsed.netloc]):
                logger.error(f"Invalid feed URL: {feed_url}")
                return False
            
            # Save to encrypted storage
            if not self._save_feed_url(feed_url):
                return False
            
            self.feed_url = feed_url
            logger.info(f"TrainerRoad feed URL set and saved securely: {parsed.netloc}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating feed URL: {e}")
            return False
    
    def fetch_ics_feed(self, timeout: int = 10) -> Optional[str]:
        """
        Fetch ICS feed content from URL.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            ICS feed content as string, or None on failure
        """
        if not self.feed_url:
            logger.warning("No feed URL configured")
            return None
        
        try:
            logger.info(f"Fetching ICS feed from {self.feed_url}")
            response = requests.get(self.feed_url, timeout=timeout)
            response.raise_for_status()
            
            content = response.text
            logger.info(f"Successfully fetched ICS feed ({len(content)} bytes)")
            return content
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching ICS feed after {timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ICS feed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching ICS feed: {e}", exc_info=True)
            return None
    
    def parse_ics_feed(self, ics_content: str) -> List[Dict[str, Any]]:
        """
        Parse ICS feed content and extract workout events.
        
        Args:
            ics_content: ICS calendar content as string
            
        Returns:
            List of workout dictionaries with normalized fields
        """
        if not ics_content:
            return []
        
        try:
            cal = Calendar.from_ical(ics_content)
            workouts = []
            
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue
                
                try:
                    workout = self._parse_event(component)
                    if workout:
                        workouts.append(workout)
                except Exception as e:
                    logger.warning(f"Error parsing event: {e}")
                    continue
            
            logger.info(f"Parsed {len(workouts)} workouts from ICS feed")
            return workouts
            
        except Exception as e:
            logger.error(f"Error parsing ICS feed: {e}", exc_info=True)
            return []
    
    def _parse_event(self, event: Event) -> Optional[Dict[str, Any]]:
        """
        Parse a single ICS event into workout dictionary.
        
        Args:
            event: iCalendar Event component
            
        Returns:
            Workout dictionary or None if not a valid workout
        """
        try:
            # Extract basic fields
            summary = str(event.get('summary', ''))
            description = str(event.get('description', ''))
            dtstart = event.get('dtstart')
            dtend = event.get('dtend')
            uid = str(event.get('uid', ''))
            
            if not summary or not dtstart:
                return None
            
            # Parse date
            if hasattr(dtstart.dt, 'date'):
                workout_date = dtstart.dt.date()
            else:
                workout_date = dtstart.dt
            
            # Calculate duration
            duration_minutes = None
            if dtend:
                if hasattr(dtstart.dt, 'date') and hasattr(dtend.dt, 'date'):
                    duration = dtend.dt - dtstart.dt
                    duration_minutes = int(duration.total_seconds() / 60)
            
            # Extract workout type from summary or description
            workout_type = self._extract_workout_type(summary, description)
            
            # Extract TSS and IF from description if available
            tss, intensity_factor = self._extract_metrics(description)
            
            return {
                'workout_id': uid or f"tr_{workout_date.isoformat()}_{hash(summary)}",
                'workout_name': summary,
                'workout_date': workout_date,
                'workout_type': workout_type,
                'duration_minutes': duration_minutes,
                'tss': tss,
                'intensity_factor': intensity_factor,
                'description': description,
                'status': 'scheduled'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing event: {e}")
            return None
    
    def _extract_workout_type(self, summary: str, description: str) -> Optional[str]:
        """
        Extract workout type from summary or description.
        
        Common TrainerRoad types: Endurance, Tempo, Threshold, VO2Max, Anaerobic, Sprint
        """
        text = f"{summary} {description}".lower()
        
        type_keywords = {
            'endurance': ['endurance', 'easy', 'recovery', 'base'],
            'tempo': ['tempo', 'sweet spot'],
            'threshold': ['threshold', 'ftp'],
            'vo2max': ['vo2', 'vo2max', 'v02'],
            'anaerobic': ['anaerobic', 'over-under'],
            'sprint': ['sprint', 'neuromuscular']
        }
        
        for workout_type, keywords in type_keywords.items():
            if any(keyword in text for keyword in keywords):
                return workout_type.capitalize()
        
        return None
    
    def _extract_metrics(self, description: str) -> tuple[Optional[float], Optional[float]]:
        """
        Extract TSS and IF from workout description.
        
        Returns:
            Tuple of (tss, intensity_factor)
        """
        import re
        
        tss = None
        intensity_factor = None
        
        # Look for TSS pattern (e.g., "TSS: 65" or "65 TSS")
        tss_match = re.search(r'(?:tss[:\s]+)?(\d+)(?:\s+tss)?', description, re.IGNORECASE)
        if tss_match:
            try:
                tss = float(tss_match.group(1))
            except ValueError:
                pass
        
        # Look for IF pattern (e.g., "IF: 0.85" or "IF 0.85")
        if_match = re.search(r'if[:\s]+([0-9.]+)', description, re.IGNORECASE)
        if if_match:
            try:
                intensity_factor = float(if_match.group(1))
            except ValueError:
                pass
        
        return tss, intensity_factor
    
    def sync_workouts(self, days_ahead: int = 14) -> Dict[str, Any]:
        """
        Sync workouts from TrainerRoad ICS feed.
        
        Args:
            days_ahead: Number of days to sync ahead
            
        Returns:
            Dictionary with sync results:
            {
                'status': 'success' | 'error',
                'workouts_synced': int,
                'workouts_updated': int,
                'workouts_created': int,
                'last_sync': datetime,
                'message': str
            }
        """
        try:
            # Check if we need to sync
            if self.last_sync:
                time_since_sync = datetime.now() - self.last_sync
                if time_since_sync.total_seconds() < self.sync_interval_hours * 3600:
                    logger.info(f"Skipping sync, last sync was {time_since_sync.total_seconds() / 3600:.1f}h ago")
                    return {
                        'status': 'skipped',
                        'message': f'Last sync was {time_since_sync.total_seconds() / 3600:.1f}h ago',
                        'last_sync': self.last_sync
                    }
            
            # Fetch ICS feed
            ics_content = self.fetch_ics_feed()
            if not ics_content:
                return {
                    'status': 'error',
                    'message': 'Failed to fetch ICS feed',
                    'workouts_synced': 0
                }
            
            # Parse workouts
            workouts = self.parse_ics_feed(ics_content)
            if not workouts:
                return {
                    'status': 'error',
                    'message': 'No workouts found in ICS feed',
                    'workouts_synced': 0
                }
            
            # Filter to upcoming workouts only
            today = date.today()
            end_date = today + timedelta(days=days_ahead)
            upcoming_workouts = [
                w for w in workouts
                if today <= w['workout_date'] <= end_date
            ]
            
            # Sync to database
            created = 0
            updated = 0
            sync_time = datetime.utcnow()
            
            for workout_data in upcoming_workouts:
                workout = WorkoutMetadata.query.filter_by(
                    workout_id=workout_data['workout_id']
                ).first()
                
                if workout:
                    # Update existing
                    workout.workout_name = workout_data['workout_name']
                    workout.workout_type = workout_data.get('workout_type')
                    workout.duration_minutes = workout_data.get('duration_minutes')
                    workout.tss = workout_data.get('tss')
                    workout.intensity_factor = workout_data.get('intensity_factor')
                    workout.synced_at = sync_time
                    updated += 1
                else:
                    # Create new
                    workout = WorkoutMetadata(
                        workout_id=workout_data['workout_id'],
                        workout_name=workout_data['workout_name'],
                        workout_date=workout_data['workout_date'],
                        workout_type=workout_data.get('workout_type'),
                        duration_minutes=workout_data.get('duration_minutes'),
                        tss=workout_data.get('tss'),
                        intensity_factor=workout_data.get('intensity_factor'),
                        status=workout_data.get('status', 'scheduled'),
                        synced_at=sync_time
                    )
                    db.session.add(workout)
                    created += 1
            
            db.session.commit()
            self.last_sync = datetime.now()
            
            logger.info(f"Synced {len(upcoming_workouts)} workouts ({created} created, {updated} updated)")
            
            return {
                'status': 'success',
                'workouts_synced': len(upcoming_workouts),
                'workouts_created': created,
                'workouts_updated': updated,
                'last_sync': self.last_sync,
                'message': f'Successfully synced {len(upcoming_workouts)} workouts'
            }
            
        except Exception as e:
            logger.error(f"Error syncing workouts: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Sync failed: {str(e)}',
                'workouts_synced': 0
            }
    
    def get_workout_constraints(self, target_date: date) -> Optional[Dict[str, Any]]:
        """
        Get normalized planning constraints for a specific date.
        
        Converts workout metadata into actionable constraints for route planning.
        
        Args:
            target_date: Date to get constraints for
            
        Returns:
            Dictionary with planning constraints or None if no workout scheduled
        """
        workout = WorkoutMetadata.get_for_date(target_date)
        
        if not workout:
            return None
        
        # Normalize to planning constraints
        constraints = {
            'has_workout': True,
            'workout_name': workout.workout_name,
            'workout_type': workout.workout_type,
            'min_duration_minutes': None,
            'max_duration_minutes': None,
            'preferred_intensity': None,
            'indoor_fallback': False,
            'notes': []
        }
        
        # Set duration constraints based on workout type
        if workout.workout_type == 'Endurance':
            # Endurance workouts can extend commute
            constraints['min_duration_minutes'] = workout.duration_minutes or 60
            constraints['max_duration_minutes'] = (workout.duration_minutes or 60) + 30
            constraints['preferred_intensity'] = 'low'
            constraints['indoor_fallback'] = False
            constraints['notes'].append('Can extend commute for endurance work')
            
        elif workout.workout_type in ['Threshold', 'VO2Max']:
            # High-intensity workouts prefer indoor
            constraints['indoor_fallback'] = True
            constraints['preferred_intensity'] = 'high'
            constraints['notes'].append('High-intensity workout - consider indoor trainer')
            
        elif workout.workout_type == 'Recovery':
            # Recovery rides should be short and easy
            constraints['max_duration_minutes'] = 45
            constraints['preferred_intensity'] = 'very_low'
            constraints['notes'].append('Keep it easy for recovery')
        
        # Add TSS-based guidance
        if workout.tss:
            if workout.tss > 100:
                constraints['notes'].append(f'High training load (TSS: {workout.tss})')
            constraints['tss'] = workout.tss
        
        return constraints


# Made with Bob