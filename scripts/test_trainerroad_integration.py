#!/usr/bin/env python3
"""
Test harness for Issue #139 - TrainerRoad ICS Integration

This script provides manual testing capabilities for QA to verify:
- ICS feed URL configuration and secure storage
- ICS feed parsing and workout extraction
- Workout metadata normalization to planning constraints
- Settings UI for TrainerRoad configuration
- Workout sync and database persistence

Usage:
    python scripts/test_trainerroad_integration.py [--test-all|--test-parser|--test-storage|--test-sync]
"""

import sys
import os
from datetime import date, datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models.workout import WorkoutMetadata
from app.services.trainerroad_service import TrainerRoadService
from src.config import Config


# Sample ICS feed content for testing
SAMPLE_ICS_FEED = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//TrainerRoad//NONSGML v1.0//EN
BEGIN:VEVENT
UID:workout-123@trainerroad.com
DTSTART:20260507T100000Z
DTEND:20260507T110000Z
SUMMARY:Endurance - Base Miles
DESCRIPTION:60 min Endurance ride\\nTSS: 45\\nIF: 0.65\\nBuild aerobic base
END:VEVENT
BEGIN:VEVENT
UID:workout-124@trainerroad.com
DTSTART:20260508T100000Z
DTEND:20260508T113000Z
SUMMARY:Threshold - Sweet Spot
DESCRIPTION:90 min Threshold intervals\\nTSS: 75\\nIF: 0.85\\n3x10min @ 90% FTP
END:VEVENT
BEGIN:VEVENT
UID:workout-125@trainerroad.com
DTSTART:20260509T100000Z
DTEND:20260509T104500Z
SUMMARY:VO2Max - Short Power
DESCRIPTION:45 min VO2Max intervals\\nTSS: 65\\nIF: 0.95\\n5x3min @ 120% FTP
END:VEVENT
END:VCALENDAR"""


def test_ics_parser():
    """Test ICS feed parsing."""
    print("\n" + "="*60)
    print("TEST: ICS Feed Parser")
    print("="*60)
    
    app = create_app()
    config = Config('config/config.yaml')
    service = TrainerRoadService(config)
    
    with app.app_context():
        # Test 1: Parse ICS feed
        print("\n1. Parsing sample ICS feed...")
        workouts = service.parse_ics_feed(SAMPLE_ICS_FEED)
        
        print(f"   ✓ Parsed {len(workouts)} workouts")
        
        if len(workouts) != 3:
            print(f"   ✗ Expected 3 workouts, got {len(workouts)}")
            return False
        
        # Test 2: Verify workout extraction
        print("\n2. Verifying workout metadata extraction...")
        
        expected_workouts = [
            {
                'name': 'Endurance - Base Miles',
                'type': 'Endurance',
                'duration': 60,
                'tss': 45,
                'intensity_factor': 0.65
            },
            {
                'name': 'Threshold - Sweet Spot',
                'type': 'Threshold',
                'duration': 90,
                'tss': 75,
                'intensity_factor': 0.85
            },
            {
                'name': 'VO2Max - Short Power',
                'type': 'VO2Max',
                'duration': 45,
                'tss': 65,
                'intensity_factor': 0.95
            }
        ]
        
        for i, (workout, expected) in enumerate(zip(workouts, expected_workouts)):
            print(f"\n   Workout {i+1}:")
            print(f"   Name: {workout['workout_name']}")
            print(f"   Type: {workout['workout_type']}")
            print(f"   Duration: {workout['duration_minutes']} min")
            print(f"   TSS: {workout.get('tss', 'N/A')}")
            print(f"   IF: {workout.get('intensity_factor', 'N/A')}")
            
            # Verify key fields
            if workout['workout_name'] != expected['name']:
                print(f"   ✗ Name mismatch")
                return False
            if workout['workout_type'] != expected['type']:
                print(f"   ✗ Type mismatch")
                return False
            if workout['duration_minutes'] != expected['duration']:
                print(f"   ✗ Duration mismatch")
                return False
            
            print(f"   ✓ Workout {i+1} parsed correctly")
        
        print("\n✅ ICS Parser Tests PASSED")
        return True


def test_secure_storage():
    """Test secure credential storage."""
    print("\n" + "="*60)
    print("TEST: Secure Credential Storage")
    print("="*60)
    
    app = create_app()
    config = Config('config/config.yaml')
    service = TrainerRoadService(config)
    
    with app.app_context():
        # Test 1: Save feed URL
        print("\n1. Testing feed URL storage...")
        test_url = "https://www.trainerroad.com/app/calendar/ics/test123"
        
        success = service.set_feed_url(test_url)
        
        if success:
            print("   ✓ Feed URL saved successfully")
        else:
            print("   ✗ Failed to save feed URL")
            return False
        
        # Test 2: Verify encryption
        print("\n2. Verifying encryption...")
        creds_path = service.credentials_path
        
        if creds_path.exists():
            print(f"   ✓ Credentials file exists: {creds_path}")
            
            # Check file permissions
            import stat
            file_stat = os.stat(creds_path)
            perms = stat.filemode(file_stat.st_mode)
            print(f"   File permissions: {perms}")
            
            if file_stat.st_mode & 0o077:
                print("   ⚠ File permissions too permissive (should be 0600)")
            else:
                print("   ✓ File permissions correct (0600)")
            
            # Verify content is encrypted
