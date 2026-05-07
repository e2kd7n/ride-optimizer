#!/usr/bin/env python3
"""
Weather Refresh Cron Job
Replaces APScheduler job for Smart Static architecture.

Run via cron: 0 */6 * * * /path/to/cron/weather_refresh.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.json_storage import JSONStorage
from app.services.weather_service import WeatherService

# Configure logging
log_dir = project_root / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'cron_weather_refresh.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Refresh weather data for active routes."""
    logger.info("=" * 60)
    logger.info("Starting weather refresh cron job")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    storage = JSONStorage()
    
    try:
        # Initialize services
        config = Config()
        weather_service = WeatherService(config)
        
        # Get home location
        home_lat = config.get('location.home.latitude')
        home_lon = config.get('location.home.longitude')
        
        if not home_lat or not home_lon:
            logger.warning("No home location configured, skipping weather refresh")
            return 0
        
        # Fetch current weather
        logger.info(f"Fetching weather for home location ({home_lat}, {home_lon})")
        weather_data = weather_service.get_current_weather(home_lat, home_lon, 'Home')
        
        # Save to cache
        cache_data = {
            'current': weather_data.get('current'),
            'forecast': weather_data.get('forecast', []),
            'updated_at': datetime.now().isoformat(),
            'location': {
                'name': 'Home',
                'latitude': home_lat,
                'longitude': home_lon
            }
        }
        storage.write('weather_cache.json', cache_data)
        
        # Record job execution
        job_record = {
            'job_type': 'weather_refresh',
            'status': 'completed',
            'started_at': start_time.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'result': {
                'location': 'Home',
                'temperature': weather_data.get('current', {}).get('temperature'),
                'comfort_score': weather_data.get('current', {}).get('comfort_score')
            }
        }
        
        # Save job history
        history = storage.read('job_history.json', default={'jobs': []})
        history['jobs'].append(job_record)
        history['jobs'] = history['jobs'][-100:]
        storage.write('job_history.json', history)
        
        logger.info(f"Weather refresh completed in {job_record['duration_seconds']:.1f}s")
        logger.info(f"Temperature: {job_record['result']['temperature']}°F")
        logger.info(f"Comfort score: {job_record['result']['comfort_score']}/100")
        
        return 0
        
    except Exception as e:
        logger.error(f"Weather refresh failed: {e}", exc_info=True)
        
        # Record failure
        job_record = {
            'job_type': 'weather_refresh',
            'status': 'failed',
            'started_at': start_time.isoformat(),
            'completed_at': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'error': str(e)
        }
        
        try:
            history = storage.read('job_history.json', default={'jobs': []})
            history['jobs'].append(job_record)
            history['jobs'] = history['jobs'][-100:]
            storage.write('job_history.json', history)
        except Exception as save_error:
            logger.error(f"Failed to save job history: {save_error}")
        
        # Don't fail hard - weather refresh is non-critical
        logger.warning("Weather refresh failed but continuing (non-critical)")
        return 0


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
