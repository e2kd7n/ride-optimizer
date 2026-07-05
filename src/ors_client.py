"""
OpenRouteService (ORS) Directions API client.

Thin fetcher mirroring src/weather_fetcher.py's pattern: single attempt,
explicit timeout, requests.exceptions.RequestException -> log + return None.
Distinguishes HTTP 429 so callers can surface a rate-limit message.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# api.openrouteservice.org is deprecated for new accounts (moved to heigit.org).
# api.heigit.org/openrouteservice works for both old and new API keys.
_ORS_DIRECTIONS_URL = "https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson"


def get_route(
    coordinates: list,
    profile: str,
    avoid_features: tuple = ("ferries",),
    api_key: str = "",
    timeout: int = 15,
) -> Optional[dict]:
    """Fetch a road-following route from ORS Directions API.

    Args:
        coordinates: List of [lon, lat] pairs (ORS uses lon, lat order).
        profile:     ORS routing profile, e.g. "cycling-regular".
        avoid_features: ORS features to avoid (default: ferries).
        api_key:     ORS API key.  Empty string means not configured.
        timeout:     HTTP request timeout in seconds.

    Returns:
        Parsed JSON response dict on success, or None on any failure.
        On HTTP 429 the returned dict is ``{"_ors_rate_limited": True}``.
    """
    if not api_key:
        logger.debug("ORS API key not configured")
        return None

    url = _ORS_DIRECTIONS_URL.format(profile=profile)
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": coordinates,
        "extra_info": ["surface", "waytype"],
        "options": {"avoid_features": list(avoid_features)},
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=timeout)
        if response.status_code == 429:
            logger.warning("ORS rate limit hit (429)")
            return {"_ors_rate_limited": True}
        if response.status_code == 404:
            # Distinguish "profile endpoint doesn't exist" (nginx 404, no JSON body with 'error.code')
            # from ORS routing errors like "no routable point" (also 404 but has error.code 2010).
            try:
                err_body = response.json()
                if isinstance(err_body.get("error"), dict) and err_body["error"].get("code"):
                    # ORS application error (routable point not found, etc) — treat as hard failure
                    logger.warning("ORS routing error %s: %s", profile, err_body["error"].get("message"))
                    return None
            except Exception:
                pass
            logger.warning("ORS profile not available (404): %s", profile)
            return {"_ors_profile_unavailable": True}
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("ORS request timed out after %ss", timeout)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("ORS request failed: %s", exc)
        return None
