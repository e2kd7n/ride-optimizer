"""
Carbon Footprint Calculator Module

Calculates carbon emissions saved by cycling instead of driving,
and provides environmental impact metrics for commute routes.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from .data_fetcher import Activity
from .route_analyzer import RouteGroup
from .units import UnitConverter

logger = logging.getLogger(__name__)


@dataclass
class CarbonFootprint:
    """Represents carbon footprint analysis for cycling activities."""
    total_distance_km: float
    total_rides: int
    co2_saved_kg: float  # CO2 emissions saved vs driving
    co2_saved_lbs: float  # CO2 in pounds
    trees_equivalent: float  # Number of trees needed to offset
    gasoline_saved_liters: float  # Gasoline saved
    gasoline_saved_gallons: float  # Gasoline in gallons
    money_saved_usd: float  # Money saved on gas
    calories_burned: int  # Approximate calories burned
    health_benefit_hours: float  # Equivalent hours of exercise
    
    # Breakdown by route
    by_route: Dict[str, Dict[str, float]] = None
    
    # Time period analysis
    daily_average_kg: float = 0.0
    weekly_average_kg: float = 0.0
    monthly_average_kg: float = 0.0
    yearly_projection_kg: float = 0.0


class CarbonCalculator:
    """Calculates carbon footprint and environmental impact of cycling."""
    
    # Emission factors (sources: EPA, IPCC)
    CO2_PER_KM_CAR = 0.171  # kg CO2 per km for average car (EPA 2023)
    CO2_PER_TREE_YEAR = 21.77  # kg CO2 absorbed by one tree per year
    LITERS_PER_100KM = 8.9  # Average car fuel consumption (EPA combined)
    USD_PER_LITER = 1.00  # Average gas price (configurable)
    CALORIES_PER_KM = 32  # Approximate calories burned cycling per km
    
    # Conversion factors
    KG_TO_LBS = 2.20462
    LITERS_TO_GALLONS = 0.264172
    
    def __init__(self, config):
        """
        Initialize carbon calculator.
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Get configurable values
        self.co2_per_km = config.get('carbon.co2_per_km_car', self.CO2_PER_KM_CAR)
        self.fuel_consumption = config.get('carbon.liters_per_100km', self.LITERS_PER_100KM)
        self.gas_price = config.get('carbon.usd_per_liter', self.USD_PER_LITER)
        self.calories_per_km = config.get('carbon.calories_per_km', self.CALORIES_PER_KM)
        
        # Initialize unit converter
        unit_system = config.get('units.system', 'metric')
        self.units = UnitConverter(unit_system)
    
    def calculate_footprint(self, activities: List[Activity],
                           route_groups: Optional[List[RouteGroup]] = None,
                           time_period_days: Optional[int] = None) -> CarbonFootprint:
        """
        Calculate carbon footprint for cycling activities.
        
        Args:
            activities: List of Activity objects (cycling activities)
            route_groups: Optional list of RouteGroup objects for breakdown
            time_period_days: Number of days in analysis period (for projections)
            
        Returns:
            CarbonFootprint object with analysis results
        """
        if not activities:
            logger.warning("No activities provided for carbon footprint calculation")
            return self._empty_footprint()
        
        # Calculate total distance
        total_distance_m = sum(act.distance for act in activities)
        total_distance_km = total_distance_m / 1000
        total_rides = len(activities)
        
        # Calculate CO2 saved (vs driving the same distance)
        co2_saved_kg = total_distance_km * self.co2_per_km
        co2_saved_lbs = co2_saved_kg * self.KG_TO_LBS
        
        # Calculate tree equivalency
        trees_equivalent = co2_saved_kg / self.CO2_PER_TREE_YEAR
        
        # Calculate gasoline saved
        gasoline_saved_liters = (total_distance_km / 100) * self.fuel_consumption
        gasoline_saved_gallons = gasoline_saved_liters * self.LITERS_TO_GALLONS
        
        # Calculate money saved
        money_saved_usd = gasoline_saved_liters * self.gas_price
        
        # Calculate calories burned
        calories_burned = int(total_distance_km * self.calories_per_km)
        
        # Calculate health benefit (WHO recommends 150 min/week moderate exercise)
        # Assume cycling is moderate exercise at ~15 km/h
        avg_speed_kmh = 15
        cycling_hours = total_distance_km / avg_speed_kmh
        health_benefit_hours = cycling_hours
        
        # Calculate time-based averages
        if time_period_days:
            daily_avg = co2_saved_kg / time_period_days
            weekly_avg = daily_avg * 7
            monthly_avg = daily_avg * 30
            yearly_projection = daily_avg * 365
        else:
            # Try to infer from activity timestamps
            daily_avg, weekly_avg, monthly_avg, yearly_projection = self._calculate_time_averages(
                activities, co2_saved_kg
            )
        
        # Calculate breakdown by route if provided
        by_route = None
        if route_groups:
            by_route = self._calculate_route_breakdown(route_groups)
        
        footprint = CarbonFootprint(
            total_distance_km=total_distance_km,
            total_rides=total_rides,
            co2_saved_kg=co2_saved_kg,
            co2_saved_lbs=co2_saved_lbs,
            trees_equivalent=trees_equivalent,
            gasoline_saved_liters=gasoline_saved_liters,
            gasoline_saved_gallons=gasoline_saved_gallons,
            money_saved_usd=money_saved_usd,
            calories_burned=calories_burned,
            health_benefit_hours=health_benefit_hours,
            by_route=by_route,
            daily_average_kg=daily_avg,
            weekly_average_kg=weekly_avg,
            monthly_average_kg=monthly_avg,
            yearly_projection_kg=yearly_projection
        )
        
        logger.info(f"Carbon footprint calculated: {co2_saved_kg:.1f} kg CO2 saved "
                   f"over {total_rides} rides ({total_distance_km:.1f} km)")
        
        return footprint
    
    def _calculate_time_averages(self, activities: List[Activity],
                                 total_co2_kg: float) -> tuple:
        """
        Calculate time-based averages from activity timestamps.
        
        Args:
            activities: List of activities
            total_co2_kg: Total CO2 saved
            
        Returns:
            Tuple of (daily_avg, weekly_avg, monthly_avg, yearly_projection)
        """
        try:
            # Parse timestamps
            timestamps = []
            for act in activities:
                if act.start_date:
                    try:
                        dt = datetime.fromisoformat(act.start_date.replace('Z', '+00:00'))
                        timestamps.append(dt)
                    except (ValueError, AttributeError):
                        continue
            
            if len(timestamps) < 2:
                # Not enough data for time-based analysis
                return 0.0, 0.0, 0.0, 0.0
            
            # Calculate time span
            earliest = min(timestamps)
            latest = max(timestamps)
            time_span_days = (latest - earliest).days + 1
            
            if time_span_days > 0:
                daily_avg = total_co2_kg / time_span_days
                weekly_avg = daily_avg * 7
                monthly_avg = daily_avg * 30
                yearly_projection = daily_avg * 365
                return daily_avg, weekly_avg, monthly_avg, yearly_projection
            
        except Exception as e:
            logger.debug(f"Failed to calculate time averages: {e}")
        
        return 0.0, 0.0, 0.0, 0.0
    
    def _calculate_route_breakdown(self, route_groups: List[RouteGroup]) -> Dict[str, Dict[str, float]]:
        """
        Calculate carbon footprint breakdown by route.
        
        Args:
            route_groups: List of RouteGroup objects
            
        Returns:
            Dictionary mapping route IDs to carbon metrics
        """
        breakdown = {}
        
        for group in route_groups:
            # Calculate total distance for this route
            total_distance_m = sum(r.distance for r in group.routes)
            total_distance_km = total_distance_m / 1000
            
            # Calculate CO2 saved
            co2_saved_kg = total_distance_km * self.co2_per_km
            
            # Calculate other metrics
            gasoline_saved_liters = (total_distance_km / 100) * self.fuel_consumption
            money_saved = gasoline_saved_liters * self.gas_price
            
            breakdown[group.id] = {
                'distance_km': total_distance_km,
                'rides': len(group.routes),
                'co2_saved_kg': co2_saved_kg,
                'gasoline_saved_liters': gasoline_saved_liters,
                'money_saved_usd': money_saved
            }
        
        return breakdown
    
    def _empty_footprint(self) -> CarbonFootprint:
        """Return empty footprint for no activities."""
        return CarbonFootprint(
            total_distance_km=0.0,
            total_rides=0,
            co2_saved_kg=0.0,
            co2_saved_lbs=0.0,
            trees_equivalent=0.0,
            gasoline_saved_liters=0.0,
            gasoline_saved_gallons=0.0,
            money_saved_usd=0.0,
            calories_burned=0,
            health_benefit_hours=0.0
        )
    
    def compare_routes_by_carbon(self, route_groups: List[RouteGroup]) -> List[tuple]:
        """
        Compare routes by carbon footprint efficiency.
        
        Args:
            route_groups: List of RouteGroup objects
            
        Returns:
            List of (RouteGroup, co2_per_ride_kg, total_co2_saved_kg) tuples
        """
        results = []
        
        for group in route_groups:
            total_distance_m = sum(r.distance for r in group.routes)
            total_distance_km = total_distance_m / 1000
            total_co2_saved = total_distance_km * self.co2_per_km
            
            if group.routes:
                co2_per_ride = total_co2_saved / len(group.routes)
            else:
                co2_per_ride = 0.0
            
            results.append((group, co2_per_ride, total_co2_saved))
        
        # Sort by total CO2 saved (highest first)
        results.sort(key=lambda x: x[2], reverse=True)
        
        return results
    
    def generate_carbon_report(self, footprint: CarbonFootprint,
                              unit_system: str = 'metric') -> Dict[str, Any]:
        """
        Generate human-readable carbon footprint report.
        
        Args:
            footprint: CarbonFootprint object
            unit_system: 'metric' or 'imperial'
            
        Returns:
            Dictionary with formatted carbon information
        """
        # Choose appropriate units
        if unit_system == 'imperial':
            distance = footprint.total_distance_km * 0.621371  # to miles
            distance_unit = 'mi'
            co2 = footprint.co2_saved_lbs
            co2_unit = 'lbs'
            fuel = footprint.gasoline_saved_gallons
            fuel_unit = 'gal'
        else:
            distance = footprint.total_distance_km
            distance_unit = 'km'
            co2 = footprint.co2_saved_kg
            co2_unit = 'kg'
            fuel = footprint.gasoline_saved_liters
            fuel_unit = 'L'
        
        report = {
            'summary': self._generate_summary(footprint, unit_system),
            'totals': {
                'distance': f"{distance:.1f} {distance_unit}",
                'rides': footprint.total_rides,
                'co2_saved': f"{co2:.1f} {co2_unit}",
                'trees_equivalent': f"{footprint.trees_equivalent:.1f} trees/year",
                'fuel_saved': f"{fuel:.1f} {fuel_unit}",
                'money_saved': f"${footprint.money_saved_usd:.2f}",
                'calories_burned': f"{footprint.calories_burned:,} cal",
                'exercise_hours': f"{footprint.health_benefit_hours:.1f} hrs"
            },
            'projections': {
                'daily': f"{footprint.daily_average_kg:.2f} kg CO2/day",
                'weekly': f"{footprint.weekly_average_kg:.1f} kg CO2/week",
                'monthly': f"{footprint.monthly_average_kg:.1f} kg CO2/month",
                'yearly': f"{footprint.yearly_projection_kg:.0f} kg CO2/year"
            },
            'environmental_impact': self._generate_impact_statements(footprint),
            'by_route': footprint.by_route
        }
        
        return report
    
    def _generate_summary(self, footprint: CarbonFootprint, unit_system: str) -> str:
        """Generate summary statement."""
        if unit_system == 'imperial':
            co2_display = f"{footprint.co2_saved_lbs:.0f} lbs"
            distance_display = f"{footprint.total_distance_km * 0.621371:.0f} miles"
        else:
            co2_display = f"{footprint.co2_saved_kg:.0f} kg"
            distance_display = f"{footprint.total_distance_km:.0f} km"
        
        return (f"By cycling {distance_display} over {footprint.total_rides} rides, "
                f"you've saved {co2_display} of CO2 emissions and "
                f"${footprint.money_saved_usd:.0f} in gas costs.")
    
    def _generate_impact_statements(self, footprint: CarbonFootprint) -> List[str]:
        """Generate impactful environmental statements."""
        statements = []
        
        # Tree equivalency
        if footprint.trees_equivalent >= 1:
            statements.append(
                f"Equivalent to planting {footprint.trees_equivalent:.0f} trees "
                f"and letting them grow for a year"
            )
        elif footprint.trees_equivalent >= 0.1:
            months = footprint.trees_equivalent * 12
            statements.append(
                f"Equivalent to {months:.0f} tree-months of carbon absorption"
            )
        
        # Gasoline saved
        if footprint.gasoline_saved_gallons >= 1:
            statements.append(
                f"Saved {footprint.gasoline_saved_gallons:.0f} gallons of gasoline"
            )
        
        # Health benefit
        if footprint.health_benefit_hours >= 2.5:
            weeks = footprint.health_benefit_hours / 2.5
            statements.append(
                f"Achieved {weeks:.1f} weeks of WHO-recommended exercise"
            )
        
        # Yearly projection
        if footprint.yearly_projection_kg >= 100:
            statements.append(
                f"On track to save {footprint.yearly_projection_kg:.0f} kg CO2 this year"
            )
        
        return statements


# Made with Bob