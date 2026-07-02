"""
Exploration Service — wraps CoverageTracker for API consumption.

Provides tile coverage, road coverage, and cache management following
the existing service patterns (constructor + initialize).
"""

import logging
from typing import Any, Dict, Optional, Tuple

from src.config_manager import ConfigManager
from src.coverage_tracker import CoverageTracker

logger = logging.getLogger(__name__)


class ExplorationService:

    def __init__(self):
        self.config = ConfigManager.get_instance()
        self._tracker = CoverageTracker(self.config)

    def initialize(self):
        pass

    def get_tile_coverage(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            result = self._tracker.get_tile_coverage(bounds, zoom=zoom)
            return {"status": "success", **result.to_dict()}
        except Exception as exc:
            logger.error("Tile coverage failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_tile_coverage_all(self, zoom: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = self._tracker.get_tile_coverage_all(zoom=zoom)
            return {"status": "success", **result.to_dict()}
        except Exception as exc:
            logger.error("Full tile coverage failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_road_coverage(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> Dict[str, Any]:
        return self._tracker.get_road_coverage(bounds)

    def invalidate_caches(self):
        self._tracker.invalidate_caches()
