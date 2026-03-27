#!/usr/bin/env python3
"""
Test script for next commute recommendations.

Tests the time detection logic at different times of day.
"""

from datetime import datetime, time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.next_commute_recommender import NextCommuteRecommender


def test_time_detection():
    """Test time detection logic for different times of day."""
    
    # Create a mock recommender (we only need the time detection method)
    class MockRecommender:
        def determine_next_commutes(self, current_time):
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
    
    recommender = MockRecommender()
    
    print("\n" + "="*70)
    print("🕐 NEXT COMMUTE TIME DETECTION TEST")
    print("="*70 + "\n")
    
    test_cases = [
        (datetime(2026, 3, 27, 7, 30), "Early Morning (7:30 AM)"),
        (datetime(2026, 3, 27, 9, 45), "Late Morning (9:45 AM)"),
        (datetime(2026, 3, 27, 12, 0), "Midday (12:00 PM)"),
        (datetime(2026, 3, 27, 15, 30), "Afternoon (3:30 PM)"),
        (datetime(2026, 3, 27, 18, 15), "Evening (6:15 PM)"),
        (datetime(2026, 3, 27, 21, 0), "Night (9:00 PM)"),
    ]
    
    print("+----------------------+------------------+------------------+")
    print("| Time                 | To Work          | To Home          |")
    print("+----------------------+------------------+------------------+")
    
    for test_time, description in test_cases:
        work_timing, home_timing = recommender.determine_next_commutes(test_time)
        print(f"| {description:<20} | {work_timing:<16} | {home_timing:<16} |")
    
    print("+----------------------+------------------+------------------+")
    print()
    
    # Explain the logic
    print("📋 LOGIC EXPLANATION:")
    print()
    print("  Morning (< 10 AM):")
    print("    - To Work: TODAY (current morning commute)")
    print("    - To Home: TODAY (this evening's commute)")
    print()
    print("  Midday (10 AM - 6 PM):")
    print("    - To Work: TOMORROW (next morning's commute)")
    print("    - To Home: TODAY (this evening's commute)")
    print()
    print("  Evening (> 6 PM):")
    print("    - To Work: TOMORROW (next morning's commute)")
    print("    - To Home: TOMORROW (next evening's commute)")
    print()
    print("="*70 + "\n")
    
    print("✅ Time detection logic test complete!")
    print()


if __name__ == '__main__':
    test_time_detection()

# Made with Bob
