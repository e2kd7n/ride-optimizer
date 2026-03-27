"""
Next Commute Recommender Module.

Provides time-aware route recommendations for the next commute to work and home,
using forecast weather conditions for appropriate time windows.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from .route_analyzer import RouteGroup
from .weather_fetcher import WeatherFetcher, WindImpactCalculator
from .units import UnitConverter

logger = logging.getLogger(__name__)


@dataclass
class CommuteRecommendation:
    """Represents a time-aware commute recommendation."""
    direction: str  # "to_work" or "to_home"
    time_window: str  # e.g., "Today 7-9 AM" or "Tomorrow 3-6 PM"
    route_group: RouteGroup
    score: float
    breakdown: Dict[str, float]
    forecast_weather: Optional[Dict[str, Any]]
    is_today: bool
    window_start: time
    window_end: time


class NextCommuteRecommender:
    """Generates time-aware recommendations for next commutes."""
    
    def __init__(self, route_groups: List[RouteGroup], config,
                 home_location: Tuple[float, float],
                 work_location: Tuple[float, float],
                 enable_weather: bool = True):
        """
        Initialize next commute recommender.
        
        Args:
            route_groups: List of RouteGroup objects
            config: Configuration object
            home_location: (lat, lon) tuple for home
            work_location: (lat, lon) tuple for work
            enable_weather: Whether to include weather analysis (default True)
        """
        self.route_groups = route_groups
        self.config = config
        self.home_location = home_location
        self.work_location = work_location
        self.enable_weather = enable_weather
        
        # Initialize unit converter
        unit_system = config.get('units.system', 'metric')
        self.units = UnitConverter(unit_system)
        
        # Get weights from config
        self.weights = {
            'time': config.get('optimization.weights.time', 0.35),
            'distance': config.get('optimization.weights.distance', 0.25),
            'safety': config.get('optimization.weights.safety', 0.25),
            'weather': config.get('optimization.weights.weather', 0.15)
        }
        
        # Initialize weather components
        self.weather_fetcher = WeatherFetcher() if enable_weather else None
        self.wind_calculator = WindImpactCalculator() if enable_weather else None
        
        # Commute time windows (configurable)
        self.morning_window_start = time(7, 0)  # 7:00 AM
        self.morning_window_end = time(9, 0)    # 9:00 AM
        self.evening_window_start = time(15, 0)  # 3:00 PM
        self.evening_window_end = time(18, 0)    # 6:00 PM
        
        # Calculate metrics for all groups (needed for scoring)
        self.metrics = {}
        self._calculate_all_metrics()
        self._find_normalization_bounds()
    
    def _calculate_all_metrics(self):
        """Calculate metrics for all route groups."""
        import numpy as np
        from .route_analyzer import RouteMetrics
        
        for group in self.route_groups:
            routes = group.routes
            
            if not routes:
                logger.warning(f"Skipping empty route group: {group.id}")
                continue
            
            durations = [r.duration for r in routes if r.duration]
            distances = [r.distance for r in routes if r.distance]
            speeds = [r.average_speed for r in routes if r.average_speed]
            elevations = [r.elevation_gain for r in routes if r.elevation_gain]
            
            avg_duration = np.mean(durations) if durations else 0
            std_duration = np.std(durations) if durations else 0
            avg_distance = np.mean(distances) if distances else 0
            avg_speed = np.mean(speeds) if speeds else 0
            avg_elevation = np.mean(elevations) if elevations else 0
            
            if avg_duration > 0:
                cv = std_duration / avg_duration
                consistency_score = max(0, 1 - cv)
            else:
                consistency_score = 0
            
            self.metrics[group.id] = RouteMetrics(
                avg_duration=avg_duration,
                std_duration=std_duration,
                avg_distance=avg_distance,
                avg_speed=avg_speed,
                avg_elevation=avg_elevation,
                consistency_score=consistency_score,
                usage_frequency=len(routes)
            )
    
    def _find_normalization_bounds(self):
        """Find min/max values for normalization."""
        if not self.metrics:
            return
        
        durations = [m.avg_duration for m in self.metrics.values()]
        distances = [m.avg_distance for m in self.metrics.values()]
        frequencies = [m.usage_frequency for m in self.metrics.values()]
        elevations = [m.avg_elevation for m in self.metrics.values()]
        
        self.min_duration = min(durations) if durations else 0
        self.max_duration = max(durations) if durations else 1
        self.min_distance = min(distances) if distances else 0
        self.max_distance = max(distances) if distances else 1
        self.max_frequency = max(frequencies) if frequencies else 1
        self.max_elevation = max(elevations) if max(elevations) > 0 else 1
    
    def determine_next_commutes(self, current_time: Optional[datetime] = None) -> Tuple[str, str]:
        """
        Determine which commutes to show based on current time.
        
        Args:
            current_time: Current datetime (defaults to now)
            
        Returns:
            Tuple of (to_work_timing, to_home_timing) where timing is:
            - "today" or "tomorrow"
        """
        if current_time is None:
            current_time = datetime.now()
        
        current_hour = current_time.hour
        
        if current_hour < 10:
            # Morning: show today's commutes
            return ("today", "today")
        elif current_hour < 18:
            # Midday: show today home, tomorrow work
            return ("tomorrow", "today")
        else:
            # Evening: show tomorrow's commutes
            return ("tomorrow", "tomorrow")
    
    def get_forecast_weather_for_window(self, lat: float, lon: float,
                                       target_date: datetime,
                                       window_start: time,
                                       window_end: time) -> Optional[Dict[str, Any]]:
        """
        Get forecast weather for a specific time window.
        
        Args:
            lat: Latitude
            lon: Longitude
            target_date: Target date
            window_start: Start time of window
            window_end: End time of window
            
        Returns:
            Dictionary with averaged weather conditions for the window
        """
        if not self.weather_fetcher:
            return None
        
        try:
            # Get hourly forecast
            hours_ahead = int((target_date - datetime.now()).total_seconds() / 3600)
            if hours_ahead < 0:
                hours_ahead = 0
            
            hourly_forecast = self.weather_fetcher.get_hourly_forecast(
                lat, lon, hours=min(hours_ahead + 24, 168)  # Up to 7 days
            )
            
            if not hourly_forecast:
                logger.warning(f"No hourly forecast available for {target_date}")
                return None
            
            # Filter forecasts for the target window
            window_forecasts = []
            for forecast in hourly_forecast:
                forecast_time = datetime.fromisoformat(forecast['timestamp'])
                
                # Check if forecast is for target date and within window
                if (forecast_time.date() == target_date.date() and
                    window_start <= forecast_time.time() <= window_end):
                    window_forecasts.append(forecast)
            
            if not window_forecasts:
                logger.warning(f"No forecasts found for window {window_start}-{window_end} on {target_date.date()}")
                return None
            
            # Average the forecasts
            import numpy as np
            avg_weather = {
                'temp_c': np.mean([f['temp_c'] for f in window_forecasts]),
                'wind_speed_kph': np.mean([f['wind_speed_kph'] for f in window_forecasts]),
                'wind_gust_kph': np.mean([f['wind_gust_kph'] for f in window_forecasts]),
                'wind_direction_deg': np.mean([f['wind_direction_deg'] for f in window_forecasts]),
                'precipitation_prob': np.mean([f['precipitation_prob'] for f in window_forecasts]),
                'num_samples': len(window_forecasts)
            }
            
            logger.info(f"Forecast for {target_date.date()} {window_start}-{window_end}: "
                       f"{avg_weather['wind_speed_kph']:.1f} km/h wind, "
                       f"{avg_weather['temp_c']:.1f}°C, "
                       f"{avg_weather['precipitation_prob']:.0f}% precip")
            
            return avg_weather
            
        except Exception as e:
            logger.error(f"Error fetching forecast weather: {e}")
            return None
    
    def calculate_route_score_with_forecast(self, route_group: RouteGroup,
                                           forecast_weather: Optional[Dict[str, Any]]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate route score using forecast weather conditions.
        
        Args:
            route_group: RouteGroup object
            forecast_weather: Forecast weather dictionary
            
        Returns:
            Tuple of (composite_score, score_breakdown)
        """
        metrics = self.metrics.get(route_group.id)
        if not metrics:
            return (0.0, {})
        
        # Calculate time score
        if self.max_duration == self.min_duration:
            duration_score = 100
        else:
            normalized = (metrics.avg_duration - self.min_duration) / (self.max_duration - self.min_duration)
            duration_score = 100 * (1 - normalized)
        consistency_bonus = metrics.consistency_score * 10
        time_score = min(100, duration_score + consistency_bonus)
        
        # Calculate distance score
        if self.max_distance == self.min_distance:
            distance_score = 100
        else:
            normalized = (metrics.avg_distance - self.min_distance) / (self.max_distance - self.min_distance)
            distance_score = 100 * (1 - normalized)
        
        # Calculate safety score
        if self.max_frequency > 0:
            frequency_score = (metrics.usage_frequency / self.max_frequency) * 100
        else:
            frequency_score = 100
        elevation_penalty = min(50, metrics.avg_elevation / 10)
        elevation_score = 100 - elevation_penalty
        road_score = metrics.consistency_score * 100
        safety_score = (frequency_score * 0.4 + elevation_score * 0.3 + road_score * 0.3)
        
        # Calculate weather score with forecast
        weather_score = 50  # Default neutral
        weather_details = None
        
        if forecast_weather and self.wind_calculator:
            try:
                # Calculate wind impact for this route
                coordinates = route_group.representative_route.coordinates
                wind_impact = self.wind_calculator.analyze_route_wind_impact(
                    coordinates,
                    forecast_weather['wind_speed_kph'],
                    forecast_weather['wind_direction_deg']
                )
                
                # Calculate weather score based on wind
                weather_score = 50
                avg_headwind = wind_impact.get('avg_headwind_kph', 0)
                
                if avg_headwind < 0:  # Tailwind
                    weather_score += min(40, abs(avg_headwind) * 2)
                else:  # Headwind
                    weather_score -= min(40, avg_headwind * 2)
                
                avg_crosswind = wind_impact.get('avg_crosswind_kph', 0)
                crosswind_penalty = min(10, avg_crosswind * 0.5)
                weather_score -= crosswind_penalty
                
                weather_score = max(0, min(100, weather_score))
                
                # Store weather details
                weather_details = {
                    **forecast_weather,
                    **wind_impact
                }
                
            except Exception as e:
                logger.error(f"Error calculating wind impact: {e}")
        
        # Calculate composite score
        composite = (
            time_score * self.weights['time'] +
            distance_score * self.weights['distance'] +
            safety_score * self.weights['safety'] +
            weather_score * self.weights['weather']
        )
        
        breakdown = {
            'time': time_score,
            'distance': distance_score,
            'safety': safety_score,
            'weather': weather_score,
            'composite': composite
        }
        
        if weather_details:
            breakdown['weather_details'] = weather_details
        
        return (composite, breakdown)
    
    def get_next_commute_recommendations(self, current_time: Optional[datetime] = None) -> Dict[str, CommuteRecommendation]:
        """
        Get time-aware recommendations for next commutes.
        
        Args:
            current_time: Current datetime (defaults to now)
            
        Returns:
            Dictionary with 'to_work' and 'to_home' recommendations
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Determine which commutes to show
        work_timing, home_timing = self.determine_next_commutes(current_time)
        
        logger.info(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Next commute to work: {work_timing}, to home: {home_timing}")
        
        recommendations = {}
        
        # Get recommendation for to_work
        work_date = current_time if work_timing == "today" else current_time + timedelta(days=1)
        work_recommendation = self._get_direction_recommendation(
            "to_work",
            work_date,
            self.morning_window_start,
            self.morning_window_end,
            work_timing == "today"
        )
        if work_recommendation:
            recommendations['to_work'] = work_recommendation
        
        # Get recommendation for to_home
        home_date = current_time if home_timing == "today" else current_time + timedelta(days=1)
        home_recommendation = self._get_direction_recommendation(
            "to_home",
            home_date,
            self.evening_window_start,
            self.evening_window_end,
            home_timing == "today"
        )
        if home_recommendation:
            recommendations['to_home'] = home_recommendation
        
        return recommendations
    
    def _get_direction_recommendation(self, direction: str, target_date: datetime,
                                     window_start: time, window_end: time,
                                     is_today: bool) -> Optional[CommuteRecommendation]:
        """
        Get recommendation for a specific direction and time window.
        
        Args:
            direction: "to_work" or "to_home"
            target_date: Target date for the commute
            window_start: Start time of commute window
            window_end: End time of commute window
            is_today: Whether this is for today
            
        Returns:
            CommuteRecommendation object or None
        """
        # Filter routes by direction
        direction_key = "home_to_work" if direction == "to_work" else "work_to_home"
        direction_routes = [g for g in self.route_groups if g.direction == direction_key]
        
        if not direction_routes:
            logger.warning(f"No routes found for direction: {direction_key}")
            return None
        
        # Get forecast weather for the time window
        # Use midpoint between home and work for weather
        mid_lat = (self.home_location[0] + self.work_location[0]) / 2
        mid_lon = (self.home_location[1] + self.work_location[1]) / 2
        
        forecast_weather = self.get_forecast_weather_for_window(
            mid_lat, mid_lon, target_date, window_start, window_end
        )
        
        # Score all routes with forecast weather
        scored_routes = []
        for route_group in direction_routes:
            score, breakdown = self.calculate_route_score_with_forecast(
                route_group, forecast_weather
            )
            scored_routes.append((route_group, score, breakdown))
        
        # Sort by score (highest first)
        scored_routes.sort(key=lambda x: x[1], reverse=True)
        
        if not scored_routes:
            return None
        
        # Get best route
        best_route, best_score, best_breakdown = scored_routes[0]
        
        # Format time window string
        day_str = "Today" if is_today else "Tomorrow"
        time_window = f"{day_str} {window_start.strftime('%I:%M %p').lstrip('0')}-{window_end.strftime('%I:%M %p').lstrip('0')}"
        
        return CommuteRecommendation(
            direction=direction,
            time_window=time_window,
            route_group=best_route,
            score=best_score,
            breakdown=best_breakdown,
            forecast_weather=forecast_weather,
            is_today=is_today,
            window_start=window_start,
            window_end=window_end
        )


# Made with Bob