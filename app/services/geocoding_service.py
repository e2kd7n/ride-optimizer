"""
Geocoding Service — forward geocoding (place name / postal code -> coordinates) via Nominatim.

Reuses the same Nominatim settings as route_naming (reverse geocoding) since both
hit the same OSM service and are subject to the same usage policy.
"""

from src.secure_logger import SecureLogger
from typing import Any, Dict

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable

from src.config_manager import ConfigManager

logger = SecureLogger(__name__)


class GeocodingService:

    def __init__(self):
        self.config = ConfigManager.get_instance()
        timeout = self.config.get('route_naming.geocoder_timeout', 10)
        user_agent = self.config.get('route_naming.geocoder_user_agent', 'strava_commute_analyzer')
        self._geolocator = Nominatim(user_agent=user_agent, timeout=timeout)

    def geocode(self, query: str) -> Dict[str, Any]:
        """Resolve a free-text location (city/state, postal code, address) to coordinates."""
        try:
            location = self._geolocator.geocode(query, exactly_one=True)
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as exc:
            logger.warning("Geocoding service unavailable: %s", exc)
            return {"status": "error", "message": "Geocoding service unavailable, try again shortly"}
        except Exception as exc:
            logger.error("Geocoding request failed: %s", exc, exc_info=True)
            return {"status": "error", "message": "Geocoding failed"}

        if location is None:
            return {"status": "error", "message": f"No location found for '{query}'"}

        return {
            "status": "success",
            "lat": location.latitude,
            "lon": location.longitude,
            "display_name": location.address,
        }
