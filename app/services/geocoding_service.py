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

# Nominatim returns full US state names; abbreviate them for the short display label.
_US_STATE_ABBREVIATIONS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC',
}


def _build_short_name(address: Dict[str, str]) -> str:
    """Condense a Nominatim ``addressdetails`` dict into 'street, city, ST'."""
    if not address:
        return None
    road = address.get('road') or address.get('pedestrian') or address.get('footway')
    house_number = address.get('house_number')
    city = (address.get('city') or address.get('town') or address.get('village')
            or address.get('hamlet') or address.get('suburb'))
    state = address.get('state')
    state = _US_STATE_ABBREVIATIONS.get(state, state)

    parts = []
    if house_number and road:
        parts.append(f'{house_number} {road}')
    elif road:
        parts.append(road)
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    return ', '.join(parts) or None


class GeocodingService:

    def __init__(self):
        self.config = ConfigManager.get_instance()
        timeout = self.config.get('route_naming.geocoder_timeout', 10)
        user_agent = self.config.get('route_naming.geocoder_user_agent', 'strava_commute_analyzer')
        self._geolocator = Nominatim(user_agent=user_agent, timeout=timeout)

    def geocode(self, query: str) -> Dict[str, Any]:
        """Resolve a free-text location (city/state, postal code, address) to coordinates.

        A bare 5-digit numeric query is assumed to be a US ZIP code (the only
        postal-code format that shape is ambiguous with internationally) and
        biased toward US results accordingly.
        """
        geocode_kwargs: Dict[str, Any] = {}
        if query.strip().isdigit() and len(query.strip()) == 5:
            geocode_kwargs['country_codes'] = 'us'

        try:
            location = self._geolocator.geocode(
                query, exactly_one=True, addressdetails=True, **geocode_kwargs
            )
        except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError) as exc:
            logger.warning("Geocoding service unavailable: %s", exc)
            return {"status": "error", "message": "Geocoding service unavailable, try again shortly"}
        except Exception as exc:
            logger.error("Geocoding request failed: %s", exc, exc_info=True)
            return {"status": "error", "message": "Geocoding failed"}

        if location is None:
            return {"status": "error", "message": f"No location found for '{query}'"}

        short_name = _build_short_name(location.raw.get('address', {}))

        return {
            "status": "success",
            "lat": location.latitude,
            "lon": location.longitude,
            "display_name": location.address,
            "short_name": short_name or location.address,
        }
