"""
Traffic Pattern Analysis Module

Analyzes commute patterns by time of day, day of week, and identifies
peak/off-peak usage patterns to help optimize route selection.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, time
from collections import defaultdict

import numpy as np

from .data_fetcher import Activity
from .route_analyzer import RouteGroup

logger = logging.getLogger(__name__)


@dataclass
class TrafficPattern:
    """Represents traffic pattern analysis for a route."""
    route_id: str
    peak_hours: List[int]  # Hours with most usage (0-23)
    off_peak_hours: List[int]  # Hours with least usage
    peak_days: List[str]  # Days with most usage
    off_peak_days: List[str]  # Days with least usage
    avg_duration_by_hour: Dict[int, float]  # Average duration by hour
    avg_duration_by_day: Dict[str, float]  # Average duration by day
    usage_by_hour: Dict[int, int]  # Count of rides by hour
    usage_by_day: Dict[str, int]  # Count of rides by day
    rush_hour_penalty: float  # Estimated time penalty during rush hour (seconds)
    best_departure_times: List[Tuple[int, str]]  # (hour, reason) tuples


class TrafficAnalyzer:
    """Analyzes traffic patterns for commute routes."""
    
    def __init__(self, config):
        """
        Initialize traffic analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Define rush hour windows (configurable)
        self.morning_rush = (
            config.get('traffic.morning_rush_start', 7),
            config.get('traffic.morning_rush_end', 9)
        )
        self.evening_rush = (
            config.get('traffic.evening_rush_start', 16),
            config.get('traffic.evening_rush_end', 18)
        )
        
        # Minimum samples needed for reliable analysis
        self.min_samples = config.get('traffic.min_samples', 5)
    
    def analyze_route_traffic(self, route_group: RouteGroup) -> TrafficPattern:
        """
        Analyze traffic patterns for a route group.
        
        Args:
            route_group: RouteGroup object with routes to analyze
            
        Returns:
            TrafficPattern object with analysis results
        """
        routes = route_group.routes
        
        if len(routes) < self.min_samples:
            logger.warning(f"Route {route_group.id} has only {len(routes)} samples, "
                          f"analysis may be unreliable (min: {self.min_samples})")
        
        # Extract timestamps and durations
        hourly_data = defaultdict(list)  # hour -> [durations]
        daily_data = defaultdict(list)   # day_name -> [durations]
        
        for route in routes:
            try:
                # Parse timestamp
                dt = datetime.fromisoformat(route.timestamp.replace('Z', '+00:00'))
                hour = dt.hour
                day_name = dt.strftime('%A')  # Monday, Tuesday, etc.
                
                # Store duration data
                hourly_data[hour].append(route.duration)
                daily_data[day_name].append(route.duration)
                
            except (ValueError, AttributeError) as e:
                logger.debug(f"Failed to parse timestamp for route {route.activity_id}: {e}")
                continue
        
        # Calculate averages and usage counts
        avg_duration_by_hour = {
            hour: np.mean(durations) 
            for hour, durations in hourly_data.items()
        }
        avg_duration_by_day = {
            day: np.mean(durations)
            for day, durations in daily_data.items()
        }
        usage_by_hour = {
            hour: len(durations)
            for hour, durations in hourly_data.items()
        }
        usage_by_day = {
            day: len(durations)
            for day, durations in daily_data.items()
        }
        
        # Identify peak and off-peak hours
        if usage_by_hour:
            sorted_hours = sorted(usage_by_hour.items(), key=lambda x: x[1], reverse=True)
            peak_hours = [h for h, _ in sorted_hours[:3]]  # Top 3 hours
            off_peak_hours = [h for h, _ in sorted_hours[-3:]]  # Bottom 3 hours
        else:
            peak_hours = []
            off_peak_hours = []
        
        # Identify peak and off-peak days
        if usage_by_day:
            sorted_days = sorted(usage_by_day.items(), key=lambda x: x[1], reverse=True)
            peak_days = [d for d, _ in sorted_days[:2]]  # Top 2 days
            off_peak_days = [d for d, _ in sorted_days[-2:]]  # Bottom 2 days
        else:
            peak_days = []
            off_peak_days = []
        
        # Calculate rush hour penalty
        rush_hour_penalty = self._calculate_rush_hour_penalty(
            avg_duration_by_hour, 
            route_group.direction
        )
        
        # Determine best departure times
        best_times = self._find_best_departure_times(
            avg_duration_by_hour,
            usage_by_hour,
            route_group.direction
        )
        
        return TrafficPattern(
            route_id=route_group.id,
            peak_hours=peak_hours,
            off_peak_hours=off_peak_hours,
            peak_days=peak_days,
            off_peak_days=off_peak_days,
            avg_duration_by_hour=avg_duration_by_hour,
            avg_duration_by_day=avg_duration_by_day,
            usage_by_hour=usage_by_hour,
            usage_by_day=usage_by_day,
            rush_hour_penalty=rush_hour_penalty,
            best_departure_times=best_times
        )
    
    def _calculate_rush_hour_penalty(self, avg_duration_by_hour: Dict[int, float],
                                     direction: str) -> float:
        """
        Calculate estimated time penalty during rush hour.
        
        Args:
            avg_duration_by_hour: Average duration by hour of day
            direction: Route direction (home_to_work or work_to_home)
            
        Returns:
            Rush hour penalty in seconds
        """
        if not avg_duration_by_hour:
            return 0.0
        
        # Determine which rush hour to analyze based on direction
        if direction == "home_to_work":
            rush_hours = range(self.morning_rush[0], self.morning_rush[1] + 1)
        else:  # work_to_home
            rush_hours = range(self.evening_rush[0], self.evening_rush[1] + 1)
        
        # Get rush hour durations
        rush_durations = [
            avg_duration_by_hour[h] 
            for h in rush_hours 
            if h in avg_duration_by_hour
        ]
        
        # Get off-peak durations (all other hours)
        off_peak_durations = [
            dur for h, dur in avg_duration_by_hour.items()
            if h not in rush_hours
        ]
        
        if not rush_durations or not off_peak_durations:
            return 0.0
        
        # Calculate penalty as difference between rush and off-peak averages
        rush_avg = np.mean(rush_durations)
        off_peak_avg = np.mean(off_peak_durations)
        penalty = max(0, rush_avg - off_peak_avg)
        
        return float(penalty)
    
    def _find_best_departure_times(self, avg_duration_by_hour: Dict[int, float],
                                   usage_by_hour: Dict[int, int],
                                   direction: str) -> List[Tuple[int, str]]:
        """
        Find optimal departure times based on duration and usage patterns.
        
        Args:
            avg_duration_by_hour: Average duration by hour
            usage_by_hour: Usage count by hour
            direction: Route direction
            
        Returns:
            List of (hour, reason) tuples for best departure times
        """
        if not avg_duration_by_hour:
            return []
        
        best_times = []
        
        # Find fastest times (top 3)
        sorted_by_duration = sorted(
            avg_duration_by_hour.items(),
            key=lambda x: x[1]
        )
        
        for hour, duration in sorted_by_duration[:3]:
            # Only recommend reasonable commute hours
            if direction == "home_to_work" and 5 <= hour <= 10:
                usage = usage_by_hour.get(hour, 0)
                reason = f"Fastest time ({duration/60:.1f} min avg, {usage} rides)"
                best_times.append((hour, reason))
            elif direction == "work_to_home" and 14 <= hour <= 20:
                usage = usage_by_hour.get(hour, 0)
                reason = f"Fastest time ({duration/60:.1f} min avg, {usage} rides)"
                best_times.append((hour, reason))
        
        # Add most popular time if not already included
        if usage_by_hour:
            most_popular_hour = max(usage_by_hour.items(), key=lambda x: x[1])[0]
            if most_popular_hour not in [h for h, _ in best_times]:
                usage = usage_by_hour[most_popular_hour]
                duration = avg_duration_by_hour[most_popular_hour]
                reason = f"Most popular ({usage} rides, {duration/60:.1f} min avg)"
                best_times.append((most_popular_hour, reason))
        
        return best_times[:3]  # Return top 3
    
    def compare_routes_by_traffic(self, route_groups: List[RouteGroup],
                                  target_hour: Optional[int] = None,
                                  target_day: Optional[str] = None) -> List[Tuple[RouteGroup, TrafficPattern, float]]:
        """
        Compare routes based on traffic patterns for a specific time.
        
        Args:
            route_groups: List of RouteGroup objects to compare
            target_hour: Hour of day to optimize for (0-23), or None for current hour
            target_day: Day of week to optimize for, or None for current day
            
        Returns:
            List of (RouteGroup, TrafficPattern, score) tuples, sorted by score
        """
        if target_hour is None:
            target_hour = datetime.now().hour
        if target_day is None:
            target_day = datetime.now().strftime('%A')
        
        results = []
        
        for group in route_groups:
            pattern = self.analyze_route_traffic(group)
            
            # Calculate score based on target time
            score = self._calculate_traffic_score(pattern, target_hour, target_day)
            
            results.append((group, pattern, score))
        
        # Sort by score (higher is better)
        results.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Compared {len(results)} routes for {target_day} at {target_hour}:00")
        for i, (group, pattern, score) in enumerate(results[:3]):
            logger.info(f"  {i+1}. {group.id}: score={score:.2f}, "
                       f"penalty={pattern.rush_hour_penalty/60:.1f}min")
        
        return results
    
    def _calculate_traffic_score(self, pattern: TrafficPattern,
                                 target_hour: int, target_day: str) -> float:
        """
        Calculate traffic score for a route at a specific time.
        
        Args:
            pattern: TrafficPattern object
            target_hour: Target hour (0-23)
            target_day: Target day name
            
        Returns:
            Score (0-100, higher is better)
        """
        score = 50.0  # Base score
        
        # Duration component (40 points)
        if target_hour in pattern.avg_duration_by_hour:
            target_duration = pattern.avg_duration_by_hour[target_hour]
            all_durations = list(pattern.avg_duration_by_hour.values())
            if all_durations:
                min_duration = min(all_durations)
                max_duration = max(all_durations)
                if max_duration > min_duration:
                    # Normalize: faster = higher score
                    normalized = 1 - (target_duration - min_duration) / (max_duration - min_duration)
                    score += normalized * 40
                else:
                    score += 40  # All durations equal
        
        # Rush hour penalty component (30 points)
        if pattern.rush_hour_penalty > 0:
            # Penalize routes with high rush hour delays
            penalty_minutes = pattern.rush_hour_penalty / 60
            penalty_score = max(0, 30 - penalty_minutes * 2)  # -2 points per minute
            score += penalty_score
        else:
            score += 30  # No penalty
        
        # Usage frequency component (20 points)
        if target_hour in pattern.usage_by_hour:
            usage = pattern.usage_by_hour[target_hour]
            max_usage = max(pattern.usage_by_hour.values()) if pattern.usage_by_hour else 1
            score += (usage / max_usage) * 20
        
        # Day of week component (10 points)
        if target_day in pattern.avg_duration_by_day:
            day_duration = pattern.avg_duration_by_day[target_day]
            all_day_durations = list(pattern.avg_duration_by_day.values())
            if all_day_durations:
                min_day_duration = min(all_day_durations)
                max_day_duration = max(all_day_durations)
                if max_day_duration > min_day_duration:
                    normalized = 1 - (day_duration - min_day_duration) / (max_day_duration - min_day_duration)
                    score += normalized * 10
                else:
                    score += 10
        
        return min(100, max(0, score))
    
    def generate_traffic_report(self, pattern: TrafficPattern) -> Dict[str, Any]:
        """
        Generate human-readable traffic report for a route.
        
        Args:
            pattern: TrafficPattern object
            
        Returns:
            Dictionary with formatted traffic information
        """
        report = {
            'route_id': pattern.route_id,
            'summary': self._generate_summary(pattern),
            'peak_hours': [f"{h}:00" for h in pattern.peak_hours],
            'off_peak_hours': [f"{h}:00" for h in pattern.off_peak_hours],
            'peak_days': pattern.peak_days,
            'off_peak_days': pattern.off_peak_days,
            'rush_hour_penalty_min': round(pattern.rush_hour_penalty / 60, 1),
            'best_departure_times': [
                {'hour': f"{h}:00", 'reason': reason}
                for h, reason in pattern.best_departure_times
            ],
            'hourly_breakdown': self._format_hourly_breakdown(pattern),
            'daily_breakdown': self._format_daily_breakdown(pattern)
        }
        
        return report
    
    def _generate_summary(self, pattern: TrafficPattern) -> str:
        """Generate summary text for traffic pattern."""
        parts = []
        
        if pattern.rush_hour_penalty > 60:
            penalty_min = pattern.rush_hour_penalty / 60
            parts.append(f"Rush hour adds ~{penalty_min:.0f} minutes")
        else:
            parts.append("Minimal rush hour impact")
        
        if pattern.best_departure_times:
            best_hour = pattern.best_departure_times[0][0]
            parts.append(f"Best departure: {best_hour}:00")
        
        if pattern.peak_days:
            parts.append(f"Busiest: {', '.join(pattern.peak_days[:2])}")
        
        return " | ".join(parts)
    
    def _format_hourly_breakdown(self, pattern: TrafficPattern) -> List[Dict[str, Any]]:
        """Format hourly data for display."""
        breakdown = []
        for hour in sorted(pattern.usage_by_hour.keys()):
            breakdown.append({
                'hour': f"{hour}:00",
                'rides': pattern.usage_by_hour[hour],
                'avg_duration_min': round(pattern.avg_duration_by_hour[hour] / 60, 1)
            })
        return breakdown
    
    def _format_daily_breakdown(self, pattern: TrafficPattern) -> List[Dict[str, Any]]:
        """Format daily data for display."""
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        breakdown = []
        for day in day_order:
            if day in pattern.usage_by_day:
                breakdown.append({
                    'day': day,
                    'rides': pattern.usage_by_day[day],
                    'avg_duration_min': round(pattern.avg_duration_by_day[day] / 60, 1)
                })
        return breakdown


# Made with Bob