"""
Service Layer for Ride Optimizer Web Platform.

This module provides a clean separation between web routes and business logic.
Services encapsulate the core functionality and can be used by both web routes
and CLI commands.

Architecture:
- Services are stateless and receive dependencies via constructor
- Services return DTOs (Data Transfer Objects) for web consumption
- Services handle all business logic and orchestration
- Services are testable in isolation

Available Services:
- AnalysisService: Core route analysis and data processing
- CommuteService: Next commute recommendations
- PlannerService: Long ride planning and recommendations
- RouteLibraryService: Route browsing and management
"""

from .analysis_service import AnalysisService
from .commute_service import CommuteService
from .planner_service import PlannerService
from .route_library_service import RouteLibraryService

__all__ = [
    'AnalysisService',
    'CommuteService',
    'PlannerService',
    'RouteLibraryService',
]

# Made with Bob
