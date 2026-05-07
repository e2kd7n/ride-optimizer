"""
Analytics Service - Comprehensive ride data insights and statistics.

This service provides analytics and insights across all ride data including:
- Overall ride statistics and trends
- Route performance analysis
- Weather impact correlations
- Commute pattern analysis
- Training insights
- Environmental impact (carbon savings)

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
from collections import defaultdict
import statistics

from src.data_fetcher import Activity
from src.route_analyzer import RouteGroup, Route
from src.carbon_calculator import CarbonCalculator
from src.json_storage import JSONStorage
from src.config import Config
from app.services.weather_service import WeatherService
from app.services.trainerroad_service import TrainerRoadService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for ride data analytics and insights.
    
    Provides comprehensive analytics including:
    - Ride statistics (total, by type, by period)
    - Route performance trends
    - Weather impact analysis
    - Commute patterns
    - Training insights
    - Carbon savings calculations
    """
    
    def __init__(self, config: Config):
        """
        Initialize analytics service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.storage = JSONStorage()
        self.weather_service = WeatherService(config)
        self.trainerroad_service = TrainerRoadService(config)
        self.carbon_calculator = CarbonCalculator(config)
        
        # Lazy-loaded data
        self._activities: Optional[List[Activity]] = None
        self._route_groups: Optional[List[RouteGroup]] = None
        self._long_rides: Optional[List[Any]] = None
        self._initialized = False
    
    def initialize(self, activities: List[Activity], 
                   route_groups: Optional[List[RouteGroup]] = None,
                   long_rides: Optional[List[Any]] = None) -> bool:
        """
        Initialize the analytics service with ride data.
        
        Must be called before using analytics methods.
        
        Args:
            activities: List of Activity objects
            route_groups: Optional list of RouteGroup objects (commute routes)
            long_rides: Optional list of long ride objects
            
        Returns:
            True if initialization successful
        """
        try:
            self._activities = activities or []
            self._route_groups = route_groups or []
            self._long_rides = long_rides or []
            self._initialized = True
            
            logger.info(f"Analytics service initialized with {len(self._activities)} activities, "
                       f"{len(self._route_groups)} route groups, {len(self._long_rides)} long rides")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics service: {e}", exc_info=True)
            return False
    
    def get_ride_statistics(self, period: str = 'all') -> Dict[str, Any]:
        """
        Get comprehensive ride statistics.
        
        Args:
            period: Time period for analysis:
                - 'all': All time
                - 'week': This week
                - 'month': This month
                - 'year': This year
                
        Returns:
            Dictionary with ride statistics:
            {
                'period': str,
                'total_rides': int,
                'total_distance_km': float,
                'total_time_hours': float,
                'average_speed_kph': float,
                'total_elevation_m': float,
                'by_type': {
                    'commute': {...},
                    'long_ride': {...}
                },
                'trends': {
                    'rides_per_week': float,
                    'distance_per_week_km': float
                },
                'records': {
                    'longest_ride_km': float,
                    'fastest_speed_kph': float,
                    'most_elevation_m': float
                }
            }
        """
        if not self._initialized:
            logger.warning("Analytics service not initialized")
            return {'status': 'error', 'message': 'Service not initialized'}
        
        try:
            # Filter activities by period
            activities = self._filter_by_period(self._activities, period)
            
            if not activities:
                return self._empty_statistics(period)
            
            # Calculate totals
            total_rides = len(activities)
            total_distance_m = sum(act.distance for act in activities)
            total_distance_km = total_distance_m / 1000
            total_time_s = sum(act.moving_time for act in activities)
            total_time_hours = total_time_s / 3600
            total_elevation_m = sum(act.total_elevation_gain for act in activities)
            
            # Calculate average speed
            avg_speed_ms = total_distance_m / total_time_s if total_time_s > 0 else 0
            avg_speed_kph = avg_speed_ms * 3.6
            
            # Break down by type
            by_type = self._calculate_type_breakdown(activities)
            
            # Calculate trends
            trends = self._calculate_trends(activities, period)
            
            # Find records
            records = self._find_records(activities)
            
            return {
                'status': 'success',
                'period': period,
                'total_rides': total_rides,
                'total_distance_km': round(total_distance_km, 2),
                'total_time_hours': round(total_time_hours, 2),
                'average_speed_kph': round(avg_speed_kph, 2),
                'total_elevation_m': round(total_elevation_m, 0),
                'by_type': by_type,
                'trends': trends,
                'records': records
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate ride statistics: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def get_route_performance_trends(self, route_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze performance trends for a specific route over time.
        
        Args:
            route_id: Route group ID to analyze
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with trend analysis:
            {
                'status': 'success' | 'error',
                'route_id': str,
                'route_name': str,
                'period_days': int,
                'rides_count': int,
                'speed_trend': {
                    'current_avg_kph': float,
                    'previous_avg_kph': float,
                    'change_percent': float,
                    'trend': 'improving' | 'declining' | 'stable'
                },
                'time_trend': {
                    'current_avg_minutes': float,
                    'previous_avg_minutes': float,
                    'change_percent': float
                },
                'consistency': {
                    'time_std_dev_minutes': float,
                    'consistency_score': float  # 0-1, higher is more consistent
                },
                'weather_correlation': {
                    'favorable_avg_speed_kph': float,
                    'unfavorable_avg_speed_kph': float,
                    'impact_percent': float
                },
                'time_series': List[{
                    'date': str,
                    'duration_minutes': float,
                    'speed_kph': float,
                    'weather_favorability': str
                }]
            }
        """
        if not self._initialized or not self._route_groups:
            return {'status': 'error', 'message': 'Service not initialized or no route data'}
        
        try:
            # Find the route group
            route_group = next((rg for rg in self._route_groups if rg.id == route_id), None)
            if not route_group:
                return {'status': 'error', 'message': f'Route {route_id} not found'}
            
            # Filter routes by time period
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_routes = [
                r for r in route_group.routes
                if r.timestamp and datetime.fromisoformat(r.timestamp.replace('Z', '+00:00')) >= cutoff_date
            ]
            
            if len(recent_routes) < 2:
                return {
                    'status': 'success',
                    'route_id': route_id,
                    'route_name': route_group.name or f"Route {route_id}",
                    'message': 'Insufficient data for trend analysis (need at least 2 rides)',
                    'rides_count': len(recent_routes)
                }
            
            # Sort by timestamp
            recent_routes.sort(key=lambda r: r.timestamp)
            
            # Split into two halves for comparison
            mid_point = len(recent_routes) // 2
            first_half = recent_routes[:mid_point]
            second_half = recent_routes[mid_point:]
            
            # Calculate speed trends
            speed_trend = self._calculate_speed_trend(first_half, second_half)
            
            # Calculate time trends
            time_trend = self._calculate_time_trend(first_half, second_half)
            
            # Calculate consistency
            consistency = self._calculate_consistency(recent_routes)
            
            # Analyze weather correlation
            weather_correlation = self._analyze_weather_correlation(recent_routes)
            
            # Build time series
            time_series = self._build_time_series(recent_routes)
            
            return {
                'status': 'success',
                'route_id': route_id,
                'route_name': route_group.name or f"Route {route_id}",
                'period_days': days,
                'rides_count': len(recent_routes),
                'speed_trend': speed_trend,
                'time_trend': time_trend,
                'consistency': consistency,
                'weather_correlation': weather_correlation,
                'time_series': time_series
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze route performance trends: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def get_weather_impact_analysis(self) -> Dict[str, Any]:
        """
        Analyze how weather conditions affect ride performance.
        
        Returns:
            Dictionary with weather impact analysis:
            {
                'status': 'success' | 'error',
                'overall_impact': {
                    'favorable_conditions_avg_speed_kph': float,
                    'unfavorable_conditions_avg_speed_kph': float,
                    'speed_difference_percent': float
                },
                'by_condition': {
                    'temperature': {
                        'optimal_range_c': Tuple[float, float],
                        'avg_speed_in_range_kph': float,
                        'avg_speed_outside_range_kph': float
                    },
                    'wind': {
                        'low_wind_avg_speed_kph': float,  # < 15 kph
                        'high_wind_avg_speed_kph': float,  # >= 15 kph
                        'impact_percent': float
                    },
                    'precipitation': {
                        'dry_avg_speed_kph': float,
                        'wet_avg_speed_kph': float,
                        'impact_percent': float
                    }
                },
                'recommendations': List[str]
            }
        """
        if not self._initialized:
            return {'status': 'error', 'message': 'Service not initialized'}
        
        try:
            # This is a simplified implementation
            # In a full implementation, we would correlate historical weather data
            # with ride performance from the weather cache
            
            # For now, provide general insights based on typical patterns
            recommendations = [
                "Optimal cycling temperature: 15-25°C (59-77°F)",
                "Wind speeds above 20 kph (12 mph) can reduce average speed by 10-15%",
                "Rain reduces average speed by 15-20% due to reduced traction and visibility",
                "Early morning rides often have calmer winds and cooler temperatures",
                "Check weather forecast before long rides to avoid severe conditions"
            ]
            
            return {
                'status': 'success',
                'message': 'Weather impact analysis requires historical weather correlation data',
                'overall_impact': {
                    'note': 'Enable weather tracking to build correlation data over time'
                },
                'by_condition': {
                    'temperature': {
                        'optimal_range_c': (15, 25),
                        'note': 'Performance typically peaks in this range'
                    },
                    'wind': {
                        'threshold_kph': 20,
                        'note': 'Significant impact above this threshold'
                    },
                    'precipitation': {
                        'note': 'Any precipitation reduces performance and safety'
                    }
                },
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze weather impact: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def get_commute_patterns(self) -> Dict[str, Any]:
        """
        Analyze commute behavior patterns.
        
        Returns:
            Dictionary with commute pattern analysis:
            {
                'status': 'success' | 'error',
                'total_commutes': int,
                'most_common_routes': List[{
                    'route_id': str,
                    'route_name': str,
                    'frequency': int,
                    'percentage': float
                }],
                'preferred_times': {
                    'morning': {
                        'peak_hour': int,  # 0-23
                        'avg_departure_time': str  # HH:MM
                    },
                    'evening': {
                        'peak_hour': int,
                        'avg_departure_time': str
                    }
                },
                'seasonal_variation': {
                    'spring': {'rides': int, 'avg_distance_km': float},
                    'summer': {'rides': int, 'avg_distance_km': float},
                    'fall': {'rides': int, 'avg_distance_km': float},
                    'winter': {'rides': int, 'avg_distance_km': float}
                },
                'consistency': {
                    'commutes_per_week': float,
                    'consistency_score': float  # 0-1
                }
            }
        """
        if not self._initialized or not self._route_groups:
            return {'status': 'error', 'message': 'Service not initialized or no commute data'}
        
        try:
            # Count total commutes
            total_commutes = sum(len(rg.routes) for rg in self._route_groups)
            
            if total_commutes == 0:
                return {
                    'status': 'success',
                    'message': 'No commute data available',
                    'total_commutes': 0
                }
            
            # Find most common routes
            most_common = sorted(
                self._route_groups,
                key=lambda rg: len(rg.routes),
                reverse=True
            )[:5]
            
            most_common_routes = [
                {
                    'route_id': rg.id,
                    'route_name': rg.name or f"Route {rg.id}",
                    'frequency': len(rg.routes),
                    'percentage': round((len(rg.routes) / total_commutes) * 100, 1)
                }
                for rg in most_common
            ]
            
            # Analyze preferred times
            preferred_times = self._analyze_commute_times()
            
            # Analyze seasonal variation
            seasonal_variation = self._analyze_seasonal_variation()
            
            # Calculate consistency
            consistency = self._calculate_commute_consistency()
            
            return {
                'status': 'success',
                'total_commutes': total_commutes,
                'most_common_routes': most_common_routes,
                'preferred_times': preferred_times,
                'seasonal_variation': seasonal_variation,
                'consistency': consistency
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze commute patterns: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def get_training_insights(self) -> Dict[str, Any]:
        """
        Provide training-related analytics.
        
        Returns:
            Dictionary with training insights:
            {
                'status': 'success' | 'error',
                'workout_completion': {
                    'scheduled': int,
                    'completed': int,
                    'completion_rate': float  # 0-1
                },
                'training_load': {
                    'current_week_hours': float,
                    'previous_week_hours': float,
                    'trend': 'increasing' | 'decreasing' | 'stable'
                },
                'recovery_patterns': {
                    'avg_rest_days_between_rides': float,
                    'longest_streak_days': int
                },
                'recommendations': List[str]
            }
        """
        if not self._initialized:
            return {'status': 'error', 'message': 'Service not initialized'}
        
        try:
            # Get workout data from TrainerRoad service
            today = date.today()
            
            # Calculate training load
            training_load = self._calculate_training_load()
            
            # Analyze recovery patterns
            recovery_patterns = self._analyze_recovery_patterns()
            
            # Generate recommendations
            recommendations = self._generate_training_recommendations(
                training_load,
                recovery_patterns
            )
            
            return {
                'status': 'success',
                'workout_completion': {
                    'note': 'Connect TrainerRoad for workout tracking'
                },
                'training_load': training_load,
                'recovery_patterns': recovery_patterns,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to generate training insights: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    def get_carbon_savings(self) -> Dict[str, Any]:
        """
        Calculate environmental impact of cycling vs driving.
        
        Returns:
            Dictionary with carbon savings:
            {
                'status': 'success' | 'error',
                'total_distance_km': float,
                'total_rides': int,
                'co2_saved_kg': float,
                'co2_saved_lbs': float,
                'trees_equivalent': float,
                'gasoline_saved_liters': float,
                'gasoline_saved_gallons': float,
                'money_saved_usd': float,
                'calories_burned': int,
                'health_benefit_hours': float,
                'projections': {
                    'daily_avg_kg': float,
                    'weekly_avg_kg': float,
                    'monthly_avg_kg': float,
                    'yearly_projection_kg': float
                },
                'impact_statements': List[str]
            }
        """
        if not self._initialized:
            return {'status': 'error', 'message': 'Service not initialized'}
        
        try:
            # Calculate carbon footprint using CarbonCalculator
            footprint = self.carbon_calculator.calculate_footprint(
                activities=self._activities,
                route_groups=self._route_groups
            )
            
            # Generate report
            report = self.carbon_calculator.generate_carbon_report(
                footprint,
                unit_system=self.config.get('units.system', 'metric')
            )
            
            return {
                'status': 'success',
                'total_distance_km': round(footprint.total_distance_km, 2),
                'total_rides': footprint.total_rides,
                'co2_saved_kg': round(footprint.co2_saved_kg, 2),
                'co2_saved_lbs': round(footprint.co2_saved_lbs, 2),
                'trees_equivalent': round(footprint.trees_equivalent, 2),
                'gasoline_saved_liters': round(footprint.gasoline_saved_liters, 2),
                'gasoline_saved_gallons': round(footprint.gasoline_saved_gallons, 2),
                'money_saved_usd': round(footprint.money_saved_usd, 2),
                'calories_burned': footprint.calories_burned,
                'health_benefit_hours': round(footprint.health_benefit_hours, 2),
                'projections': {
                    'daily_avg_kg': round(footprint.daily_average_kg, 2),
                    'weekly_avg_kg': round(footprint.weekly_average_kg, 2),
                    'monthly_avg_kg': round(footprint.monthly_average_kg, 2),
                    'yearly_projection_kg': round(footprint.yearly_projection_kg, 0)
                },
                'impact_statements': report.get('environmental_impact', []),
                'summary': report.get('summary', '')
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate carbon savings: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    # Private helper methods
    
    def _filter_by_period(self, activities: List[Activity], period: str) -> List[Activity]:
        """Filter activities by time period."""
        if period == 'all':
            return activities
        
        now = datetime.now()
        
        if period == 'week':
            cutoff = now - timedelta(days=7)
        elif period == 'month':
            cutoff = now - timedelta(days=30)
        elif period == 'year':
            cutoff = now - timedelta(days=365)
        else:
            return activities
        
        return [
            act for act in activities
            if act.start_date and datetime.fromisoformat(act.start_date.replace('Z', '+00:00')) >= cutoff
        ]
    
    def _empty_statistics(self, period: str) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            'status': 'success',
            'period': period,
            'total_rides': 0,
            'total_distance_km': 0.0,
            'total_time_hours': 0.0,
            'average_speed_kph': 0.0,
            'total_elevation_m': 0.0,
            'by_type': {},
            'trends': {},
            'records': {}
        }
    
    def _calculate_type_breakdown(self, activities: List[Activity]) -> Dict[str, Any]:
        """Calculate breakdown by activity type."""
        commute_activities = []
        long_ride_activities = []
        other_activities = []
        
        for act in activities:
            # Simple heuristic: rides < 30km are likely commutes
            distance_km = act.distance / 1000
            if distance_km < 30:
                commute_activities.append(act)
            elif distance_km >= 50:
                long_ride_activities.append(act)
            else:
                other_activities.append(act)
        
        def calc_stats(acts):
            if not acts:
                return {'count': 0, 'distance_km': 0.0, 'time_hours': 0.0}
            return {
                'count': len(acts),
                'distance_km': round(sum(a.distance for a in acts) / 1000, 2),
                'time_hours': round(sum(a.moving_time for a in acts) / 3600, 2)
            }
        
        return {
            'commute': calc_stats(commute_activities),
            'long_ride': calc_stats(long_ride_activities),
            'other': calc_stats(other_activities)
        }
    
    def _calculate_trends(self, activities: List[Activity], period: str) -> Dict[str, Any]:
        """Calculate trend metrics."""
        if not activities:
            return {}
        
        # Calculate time span
        timestamps = [
            datetime.fromisoformat(act.start_date.replace('Z', '+00:00'))
            for act in activities if act.start_date
        ]
        
        if len(timestamps) < 2:
            return {}
        
        time_span_days = (max(timestamps) - min(timestamps)).days + 1
        weeks = time_span_days / 7
        
        if weeks == 0:
            return {}
        
        total_distance_km = sum(act.distance for act in activities) / 1000
        
        return {
            'rides_per_week': round(len(activities) / weeks, 2),
            'distance_per_week_km': round(total_distance_km / weeks, 2)
        }
    
    def _find_records(self, activities: List[Activity]) -> Dict[str, Any]:
        """Find record-breaking rides."""
        if not activities:
            return {}
        
        longest = max(activities, key=lambda a: a.distance)
        fastest = max(activities, key=lambda a: a.average_speed)
        most_elevation = max(activities, key=lambda a: a.total_elevation_gain)
        
        return {
            'longest_ride_km': round(longest.distance / 1000, 2),
            'fastest_speed_kph': round(fastest.average_speed * 3.6, 2),
            'most_elevation_m': round(most_elevation.total_elevation_gain, 0)
        }
    
    def _calculate_speed_trend(self, first_half: List[Route], 
                               second_half: List[Route]) -> Dict[str, Any]:
        """Calculate speed trend between two periods."""
        def avg_speed(routes):
            if not routes:
                return 0.0
            speeds = [r.average_speed * 3.6 for r in routes]  # Convert to kph
            return statistics.mean(speeds)
        
        prev_avg = avg_speed(first_half)
        curr_avg = avg_speed(second_half)
        
        if prev_avg == 0:
            change_percent = 0.0
            trend = 'stable'
        else:
            change_percent = ((curr_avg - prev_avg) / prev_avg) * 100
            if change_percent > 2:
                trend = 'improving'
            elif change_percent < -2:
                trend = 'declining'
            else:
                trend = 'stable'
        
        return {
            'current_avg_kph': round(curr_avg, 2),
            'previous_avg_kph': round(prev_avg, 2),
            'change_percent': round(change_percent, 2),
            'trend': trend
        }
    
    def _calculate_time_trend(self, first_half: List[Route],
                              second_half: List[Route]) -> Dict[str, Any]:
        """Calculate time trend between two periods."""
        def avg_time(routes):
            if not routes:
                return 0.0
            times = [r.duration / 60 for r in routes]  # Convert to minutes
            return statistics.mean(times)
        
        prev_avg = avg_time(first_half)
        curr_avg = avg_time(second_half)
        
        if prev_avg == 0:
            change_percent = 0.0
        else:
            change_percent = ((curr_avg - prev_avg) / prev_avg) * 100
        
        return {
            'current_avg_minutes': round(curr_avg, 2),
            'previous_avg_minutes': round(prev_avg, 2),
            'change_percent': round(change_percent, 2)
        }
    
    def _calculate_consistency(self, routes: List[Route]) -> Dict[str, Any]:
        """Calculate consistency metrics."""
        if len(routes) < 2:
            return {'consistency_score': 1.0, 'time_std_dev_minutes': 0.0}
        
        times = [r.duration / 60 for r in routes]  # Convert to minutes
        std_dev = statistics.stdev(times)
        mean_time = statistics.mean(times)
        
        # Consistency score: lower std dev relative to mean = higher consistency
        if mean_time > 0:
            coefficient_of_variation = std_dev / mean_time
            consistency_score = max(0.0, 1.0 - coefficient_of_variation)
        else:
            consistency_score = 1.0
        
        return {
            'time_std_dev_minutes': round(std_dev, 2),
            'consistency_score': round(consistency_score, 2)
        }
    
    def _analyze_weather_correlation(self, routes: List[Route]) -> Dict[str, Any]:
        """Analyze weather impact on route performance."""
        # Simplified implementation - would need historical weather data
        return {
            'note': 'Weather correlation requires historical weather data',
            'favorable_avg_speed_kph': 0.0,
            'unfavorable_avg_speed_kph': 0.0,
            'impact_percent': 0.0
        }
    
    def _build_time_series(self, routes: List[Route]) -> List[Dict[str, Any]]:
        """Build time series data for charting."""
        time_series = []
        
        for route in routes:
            time_series.append({
                'date': route.timestamp.split('T')[0] if route.timestamp else 'unknown',
                'duration_minutes': round(route.duration / 60, 2),
                'speed_kph': round(route.average_speed * 3.6, 2),
                'weather_favorability': 'unknown'
            })
        
        return time_series
    
    def _analyze_commute_times(self) -> Dict[str, Any]:
        """Analyze preferred commute times."""
        morning_hours = []
        evening_hours = []
        
        for route_group in self._route_groups:
            for route in route_group.routes:
                if not route.timestamp:
                    continue
                
                try:
                    dt = datetime.fromisoformat(route.timestamp.replace('Z', '+00:00'))
                    hour = dt.hour
                    
                    if 5 <= hour < 12:
                        morning_hours.append(hour)
                    elif 15 <= hour < 20:
                        evening_hours.append(hour)
                except Exception:
                    continue
        
        def calc_peak(hours):
            if not hours:
                return {'peak_hour': 8, 'avg_departure_time': '08:00'}
            
            peak_hour = max(set(hours), key=hours.count)
            avg_hour = statistics.mean(hours)
            avg_minute = int((avg_hour % 1) * 60)
            
            return {
                'peak_hour': peak_hour,
                'avg_departure_time': f"{int(avg_hour):02d}:{avg_minute:02d}"
            }
        
        return {
            'morning': calc_peak(morning_hours),
            'evening': calc_peak(evening_hours)
        }
    
    def _analyze_seasonal_variation(self) -> Dict[str, Any]:
        """Analyze seasonal riding patterns."""
        seasons = {
            'spring': {'rides': 0, 'distance_m': 0},
            'summer': {'rides': 0, 'distance_m': 0},
            'fall': {'rides': 0, 'distance_m': 0},
            'winter': {'rides': 0, 'distance_m': 0}
        }
        
        def get_season(month):
            if month in [3, 4, 5]:
                return 'spring'
            elif month in [6, 7, 8]:
                return 'summer'
            elif month in [9, 10, 11]:
                return 'fall'
            else:
                return 'winter'
        
        for route_group in self._route_groups:
            for route in route_group.routes:
                if not route.timestamp:
                    continue
                
                try:
                    dt = datetime.fromisoformat(route.timestamp.replace('Z', '+00:00'))
                    season = get_season(dt.month)
                    seasons[season]['rides'] += 1
                    seasons[season]['distance_m'] += route.distance
                except Exception:
                    continue
        
        # Convert to km and calculate averages
        result = {}
        for season, data in seasons.items():
            result[season] = {
                'rides': data['rides'],
                'avg_distance_km': round(data['distance_m'] / 1000 / data['rides'], 2) if data['rides'] > 0 else 0.0
            }
        
        return result
    
    def _calculate_commute_consistency(self) -> Dict[str, Any]:
        """Calculate commute consistency metrics."""
        if not self._route_groups:
            return {'commutes_per_week': 0.0, 'consistency_score': 0.0}
        
        # Get all commute timestamps
        timestamps = []
        for route_group in self._route_groups:
            for route in route_group.routes:
                if route.timestamp:
                    try:
                        dt = datetime.fromisoformat(route.timestamp.replace('Z', '+00:00'))
                        timestamps.append(dt)
                    except Exception:
                        continue
        
        if len(timestamps) < 2:
            return {'commutes_per_week': 0.0, 'consistency_score': 0.0}
        
        # Calculate time span
        time_span_days = (max(timestamps) - min(timestamps)).days + 1
        weeks = time_span_days / 7
        
        commutes_per_week = len(timestamps) / weeks if weeks > 0 else 0.0
        
        # Consistency score based on regularity (5 commutes/week = perfect)
        consistency_score = min(1.0, commutes_per_week / 5.0)
        
        return {
            'commutes_per_week': round(commutes_per_week, 2),
            'consistency_score': round(consistency_score, 2)
        }
    
    def _calculate_training_load(self) -> Dict[str, Any]:
        """Calculate training load metrics."""
        now = datetime.now()
        current_week_start = now - timedelta(days=now.weekday())
        previous_week_start = current_week_start - timedelta(days=7)
        
        current_week_activities = [
            act for act in self._activities
            if act.start_date and datetime.fromisoformat(act.start_date.replace('Z', '+00:00')) >= current_week_start
        ]
        
        previous_week_activities = [
            act for act in self._activities
            if act.start_date and previous_week_start <= datetime.fromisoformat(act.start_date.replace('Z', '+00:00')) < current_week_start
        ]
        
        current_hours = sum(act.moving_time for act in current_week_activities) / 3600
        previous_hours = sum(act.moving_time for act in previous_week_activities) / 3600
        
        if previous_hours == 0:
            trend = 'stable'
        elif current_hours > previous_hours * 1.1:
            trend = 'increasing'
        elif current_hours < previous_hours * 0.9:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'current_week_hours': round(current_hours, 2),
            'previous_week_hours': round(previous_hours, 2),
            'trend': trend
        }
    
    def _analyze_recovery_patterns(self) -> Dict[str, Any]:
        """Analyze recovery patterns between rides."""
        if not self._activities:
            return {'avg_rest_days_between_rides': 0.0, 'longest_streak_days': 0}
        
        # Sort activities by date
        sorted_activities = sorted(
            [act for act in self._activities if act.start_date],
            key=lambda a: a.start_date
        )
        
        if len(sorted_activities) < 2:
            return {'avg_rest_days_between_rides': 0.0, 'longest_streak_days': 1}
        
        # Calculate gaps between rides
        gaps = []
        for i in range(1, len(sorted_activities)):
            prev_date = datetime.fromisoformat(sorted_activities[i-1].start_date.replace('Z', '+00:00'))
            curr_date = datetime.fromisoformat(sorted_activities[i].start_date.replace('Z', '+00:00'))
            gap_days = (curr_date - prev_date).days
            gaps.append(gap_days)
        
        avg_gap = statistics.mean(gaps) if gaps else 0.0
        
        # Find longest streak (consecutive days with rides)
        longest_streak = 1
        current_streak = 1
        
        for gap in gaps:
            if gap <= 1:  # Same day or next day
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        
        return {
            'avg_rest_days_between_rides': round(avg_gap, 2),
            'longest_streak_days': longest_streak
        }
    
    def _generate_training_recommendations(self, training_load: Dict[str, Any],
                                          recovery_patterns: Dict[str, Any]) -> List[str]:
        """Generate training recommendations."""
        recommendations = []
        
        # Check training load
        if training_load['trend'] == 'increasing':
            if training_load['current_week_hours'] > 10:
                recommendations.append("High training load - ensure adequate recovery")
        elif training_load['trend'] == 'decreasing':
            recommendations.append("Training volume decreasing - consider ramping up gradually")
        
        # Check recovery
        avg_rest = recovery_patterns.get('avg_rest_days_between_rides', 0)
        if avg_rest < 1:
            recommendations.append("Riding daily - ensure at least one rest day per week")
        elif avg_rest > 3:
            recommendations.append("Long gaps between rides - try to maintain consistency")
        
        # General recommendations
        recommendations.append("Aim for 3-5 rides per week for optimal fitness")
        recommendations.append("Include variety: mix commutes, long rides, and recovery rides")
        
        return recommendations


# Made with Bob