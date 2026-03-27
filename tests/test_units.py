"""
Unit tests for units module.
"""
import pytest
from src.units import UnitConverter


class TestUnitConverter:
    """Test unit conversion functionality."""
    
    def test_metric_distance(self):
        """Test metric distance conversion."""
        converter = UnitConverter('metric')
        assert converter.distance(1000) == "1.00 km"
        assert converter.distance(500) == "0.50 km"
        assert converter.distance(1500, precision=1) == "1.5 km"
    
    def test_imperial_distance(self):
        """Test imperial distance conversion."""
        converter = UnitConverter('imperial')
        assert converter.distance(1609.34) == "1.00 mi"
        assert converter.distance(804.67) == "0.50 mi"
    
    def test_metric_speed(self):
        """Test metric speed conversion."""
        converter = UnitConverter('metric')
        # 10 m/s = 36 km/h
        assert converter.speed(10) == "36.0 km/h"
        assert converter.speed(5) == "18.0 km/h"
    
    def test_imperial_speed(self):
        """Test imperial speed conversion."""
        converter = UnitConverter('imperial')
        # 10 m/s ≈ 22.4 mph
        result = converter.speed(10)
        assert "22." in result and "mph" in result
    
    def test_metric_wind_speed(self):
        """Test metric wind speed conversion."""
        converter = UnitConverter('metric')
        # Metric wind speed is kept in m/s (common in weather)
        assert converter.wind_speed(10) == "10.0 m/s"
    
    def test_imperial_wind_speed(self):
        """Test imperial wind speed conversion."""
        converter = UnitConverter('imperial')
        result = converter.wind_speed(10)
        assert "mph" in result
    
    def test_metric_temperature(self):
        """Test metric temperature conversion."""
        converter = UnitConverter('metric')
        assert converter.temperature(20) == "20.0°C"
        assert converter.temperature(0) == "0.0°C"
    
    def test_imperial_temperature(self):
        """Test imperial temperature conversion."""
        converter = UnitConverter('imperial')
        assert converter.temperature(0) == "32.0°F"
        assert converter.temperature(100) == "212.0°F"
    
    def test_metric_elevation(self):
        """Test metric elevation conversion."""
        converter = UnitConverter('metric')
        assert converter.elevation(100) == "100 m"
        assert converter.elevation(1500) == "1500 m"
    
    def test_imperial_elevation(self):
        """Test imperial elevation conversion."""
        converter = UnitConverter('imperial')
        # 100m ≈ 328 ft
        result = converter.elevation(100)
        assert "ft" in result
        assert "328" in result
    
    def test_distance_value(self):
        """Test raw distance value conversion."""
        converter = UnitConverter('metric')
        assert converter.distance_value(1000) == 1.0
        
        converter = UnitConverter('imperial')
        assert abs(converter.distance_value(1609.34) - 1.0) < 0.01
    
    def test_speed_value(self):
        """Test raw speed value conversion."""
        converter = UnitConverter('metric')
        assert converter.speed_value(10) == 36.0
        
        converter = UnitConverter('imperial')
        result = converter.speed_value(10)
        assert 22 < result < 23
    
    def test_invalid_system(self):
        """Test that invalid unit system defaults to metric."""
        converter = UnitConverter('invalid')
        # Should default to metric
        assert converter.distance(1000) == "1.00 km"

# Made with Bob
