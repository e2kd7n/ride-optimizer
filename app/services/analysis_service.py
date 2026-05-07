"""
Analysis Service - Core route analysis and data processing.

This service orchestrates the main analysis workflow:
- Fetching activities from Strava
- Analyzing routes and grouping similar routes
- Processing long rides
- Managing data freshness and caching
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from src.data_fetcher import StravaDataFetcher, Activity
from src.route_analyzer import RouteAnalyzer, RouteGroup
from src.long_ride_analyzer import LongRideAnalyzer, LongRide
from src.location_finder import LocationFinder, Location
from src.config import Config
from src.auth import get_authenticated_client

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Service for core route analysis and data processing.
    
    This service provides a clean interface for:
    - Running full analysis (fetch + analyze)
    - Getting analysis status and freshness
    - Accessing analyzed data (route groups, long rides)
    - Managing cache and data lifecycle
    """
    
    def __init__(self, config: Config):
        """
        Initialize analysis service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self._auth_available = False
        self.data_fetcher = None
        
        # Try to create authenticated Strava client
        try:
            client = get_authenticated_client(config)
            self.data_fetcher = StravaDataFetcher(client, config, use_test_cache=False)
            self._auth_available = True
            logger.info("AnalysisService initialized with Strava authentication")
        except (ValueError, Exception) as e:
            logger.warning(f"AnalysisService initialized without Strava auth: {e}")
            logger.warning("Service will operate in degraded mode with cached data only")
        
        # LocationFinder will be created on-demand during analysis
        self._location_finder: Optional[LocationFinder] = None
        
        # Cached analysis results
        self._activities: Optional[List[Activity]] = None
        self._route_groups: Optional[List[RouteGroup]] = None
        self._long_rides: Optional[List[LongRide]] = None
        self._home_location: Optional[Location] = None
        self._work_location: Optional[Location] = None
        self._last_analysis_time: Optional[datetime] = None
    
    def run_full_analysis(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Run complete analysis workflow.
        
        Steps:
        1. Fetch activities from Strava
        2. Find home and work locations
        3. Analyze and group routes
        4. Analyze long rides
        5. Cache results
        
        Args:
            force_refresh: If True, bypass cache and re-fetch data
            
        Returns:
            Dictionary with analysis summary:
            {
                'status': 'success' | 'error',
                'message': str,
                'activities_count': int,
                'route_groups_count': int,
                'long_rides_count': int,
                'analysis_time': str (ISO format),
                'data_freshness': 'fresh' | 'stale',
                'errors': List[str]
            }
        """
        logger.info(f"Starting full analysis (force_refresh={force_refresh})")
        errors = []
        
        try:
            # Step 1: Fetch activities
            logger.info("Fetching activities from Strava...")
            self._activities = self.data_fetcher.fetch_activities(force_refresh=force_refresh)
            logger.info(f"Fetched {len(self._activities)} activities")
            
            if not self._activities:
                return {
                    'status': 'error',
                    'message': 'No activities found',
                    'activities_count': 0,
                    'route_groups_count': 0,
                    'long_rides_count': 0,
                    'analysis_time': datetime.now().isoformat(),
                    'data_freshness': 'unknown',
                    'errors': ['No activities available for analysis']
                }
            
            # Step 2: Find locations
            logger.info("Finding home and work locations...")
            if self._location_finder is None:
                self._location_finder = LocationFinder(self._activities, self.config)
            self._home_location, self._work_location = self._location_finder.find_locations(
                self._activities
            )
            logger.info(f"Home: {self._home_location.name}, Work: {self._work_location.name}")
            
            # Step 3: Analyze routes
            logger.info("Analyzing and grouping routes...")
            route_analyzer = RouteAnalyzer(
                activities=self._activities,
                home=self._home_location,
                work=self._work_location,
                config=self.config,
                force_reanalysis=force_refresh
            )
            
            self._route_groups = route_analyzer.analyze_routes()
            logger.info(f"Found {len(self._route_groups)} route groups")
            
            # Step 4: Analyze long rides
            logger.info("Analyzing long rides...")
            long_ride_analyzer = LongRideAnalyzer(
                activities=self._activities,
                config=self.config
            )
            
            # Get commute activities from route groups
            commute_activity_ids = set()
            for group in self._route_groups:
                for route in group.routes:
                    commute_activity_ids.add(route.activity_id)
            
            commute_activities = [
                a for a in self._activities 
                if a.id in commute_activity_ids
            ]
            
            _, long_ride_activities = long_ride_analyzer.classify_activities(commute_activities)
            self._long_rides = long_ride_analyzer.group_similar_rides(long_ride_activities)
            logger.info(f"Found {len(self._long_rides)} unique long rides")
            
            # Step 5: Update analysis time
            self._last_analysis_time = datetime.now()
            
            return {
                'status': 'success',
                'message': 'Analysis completed successfully',
                'activities_count': len(self._activities),
                'route_groups_count': len(self._route_groups),
                'long_rides_count': len(self._long_rides),
                'analysis_time': self._last_analysis_time.isoformat(),
                'data_freshness': 'fresh',
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Analysis failed: {str(e)}',
                'activities_count': len(self._activities) if self._activities else 0,
                'route_groups_count': 0,
                'long_rides_count': 0,
                'analysis_time': datetime.now().isoformat(),
                'data_freshness': 'unknown',
                'errors': [str(e)]
            }
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """
        Get current analysis status without running analysis.
        
        Returns:
            Dictionary with status information:
            {
                'has_data': bool,
                'last_analysis': str | None (ISO format),
                'activities_count': int,
                'route_groups_count': int,
                'long_rides_count': int,
                'data_age_hours': float | None,
                'is_stale': bool
            }
        """
        has_data = (
            self._activities is not None and
            self._route_groups is not None and
            self._long_rides is not None
        )
        
        data_age_hours = None
        is_stale = True
        
        if self._last_analysis_time:
            age = datetime.now() - self._last_analysis_time
            data_age_hours = age.total_seconds() / 3600
            # Consider data stale after 24 hours
            is_stale = data_age_hours > 24
        
        return {
            'has_data': has_data,
            'last_analysis': self._last_analysis_time.isoformat() if self._last_analysis_time else None,
            'activities_count': len(self._activities) if self._activities else 0,
            'route_groups_count': len(self._route_groups) if self._route_groups else 0,
            'long_rides_count': len(self._long_rides) if self._long_rides else 0,
            'data_age_hours': data_age_hours,
            'is_stale': is_stale
        }
    
    def get_route_groups(self) -> List[RouteGroup]:
        """
        Get analyzed route groups.
        
        Returns:
            List of RouteGroup objects, or empty list if no analysis has been run
        """
        return self._route_groups if self._route_groups else []
    
    def get_long_rides(self) -> List[LongRide]:
        """
        Get analyzed long rides.
        
        Returns:
            List of LongRide objects, or empty list if no analysis has been run
        """
        return self._long_rides if self._long_rides else []
    
    def get_activities(self) -> List[Activity]:
        """
        Get all activities.
        
        Returns:
            List of Activity objects, or empty list if no data has been fetched
        """
        return self._activities if self._activities else []
    
    def get_locations(self) -> Tuple[Optional[Location], Optional[Location]]:
        """
        Get home and work locations.
        
        Returns:
            Tuple of (home_location, work_location), or (None, None) if not found
        """
        return (self._home_location, self._work_location)
    
    def clear_cache(self):
        """Clear all cached analysis data."""
        logger.info("Clearing analysis cache")
        self._activities = None
        self._route_groups = None
        self._long_rides = None
        self._home_location = None
        self._work_location = None
        self._last_analysis_time = None

# Made with Bob
