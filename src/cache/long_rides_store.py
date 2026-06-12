"""
Persistence layer for long-ride analysis results.

Serializes LongRide objects to JSON so the API can reload them after
restart without re-running the full Strava analysis pipeline.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..long_ride_analyzer import LongRide

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_PATH = Path("data/cache/long_rides_store.json")


class LongRidesDataStore:
    """
    JSON-backed persistence store for LongRide objects.

    Usage::

        store = LongRidesDataStore()
        store.save(long_rides)          # write
        rides = store.load()            # read
        store.invalidate()              # clear
        info = store.stats()            # metadata
    """

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = Path(cache_path) if cache_path else _DEFAULT_CACHE_PATH
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, rides: List[LongRide]) -> None:
        """Serialize *rides* to disk, replacing any existing cache."""
        payload = {
            "version": 1,
            "saved_at": datetime.utcnow().isoformat(),
            "count": len(rides),
            "rides": [self._serialize(r) for r in rides],
        }
        try:
            self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.info("LongRidesDataStore: saved %d rides to %s", len(rides), self.cache_path)
        except OSError as exc:
            logger.warning("LongRidesDataStore: failed to save cache: %s", exc)

    def load(self) -> List[LongRide]:
        """
        Deserialize rides from disk.

        Returns an empty list when the cache is missing or corrupt.
        """
        if not self.cache_path.exists():
            logger.debug("LongRidesDataStore: no cache at %s", self.cache_path)
            return []
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            rides = [self._deserialize(d) for d in raw.get("rides", [])]
            logger.info("LongRidesDataStore: loaded %d rides from %s", len(rides), self.cache_path)
            return rides
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("LongRidesDataStore: corrupt cache, discarding (%s)", exc)
            return []

    def invalidate(self) -> None:
        """Delete the cache file."""
        if self.cache_path.exists():
            self.cache_path.unlink()
            logger.info("LongRidesDataStore: cache invalidated")

    def is_valid(self) -> bool:
        """Return True when a non-empty cache file exists."""
        return self.cache_path.exists() and self.cache_path.stat().st_size > 0

    def stats(self) -> Dict[str, Any]:
        """
        Return metadata about the current cache.

        Keys: ``exists``, ``count``, ``saved_at``, ``size_bytes``.
        """
        if not self.cache_path.exists():
            return {"exists": False, "count": 0, "saved_at": None, "size_bytes": 0}
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return {
                "exists": True,
                "count": raw.get("count", 0),
                "saved_at": raw.get("saved_at"),
                "size_bytes": self.cache_path.stat().st_size,
            }
        except (json.JSONDecodeError, OSError):
            return {
                "exists": True,
                "count": 0,
                "saved_at": None,
                "size_bytes": self.cache_path.stat().st_size,
            }

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(ride: LongRide) -> Dict[str, Any]:
        return {
            "activity_id": ride.activity_id,
            "name": ride.name,
            "coordinates": list(ride.coordinates),
            "distance": ride.distance,
            "duration": ride.duration,
            "elevation_gain": ride.elevation_gain,
            "timestamp": ride.timestamp,
            "average_speed": ride.average_speed,
            "start_location": list(ride.start_location),
            "end_location": list(ride.end_location),
            "is_loop": ride.is_loop,
            "type": ride.type,
            "uses": ride.uses,
            "activity_ids": ride.activity_ids or [],
            "activity_dates": ride.activity_dates or [],
        }

    @staticmethod
    def _deserialize(data: Dict[str, Any]) -> LongRide:
        return LongRide(
            activity_id=data["activity_id"],
            name=data["name"],
            coordinates=[tuple(c) for c in data.get("coordinates", [])],
            distance=float(data["distance"]),
            duration=int(data["duration"]),
            elevation_gain=float(data["elevation_gain"]),
            timestamp=data["timestamp"],
            average_speed=float(data["average_speed"]),
            start_location=tuple(data["start_location"]),
            end_location=tuple(data["end_location"]),
            is_loop=bool(data["is_loop"]),
            type=data["type"],
            uses=int(data.get("uses", 1)),
            activity_ids=data.get("activity_ids") or None,
            activity_dates=data.get("activity_dates") or None,
        )
