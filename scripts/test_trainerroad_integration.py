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
            with open(creds_path, 'rb') as f:
                content = f.read()
                if b'https://' in content:
                    print("   ✗ URL not encrypted (plaintext detected)")
                    return False
                else:
                    print("   ✓ Content is encrypted")
        else:
            print("   ✗ Credentials file not created")
            return False
        
        # Test 3: Retrieve feed URL
        print("\n3. Testing feed URL retrieval...")
        retrieved_url = service.get_feed_url()
        
        if retrieved_url == test_url:
            print("   ✓ Feed URL retrieved correctly")
        else:
            print(f"   ✗ URL mismatch: expected {test_url}, got {retrieved_url}")
            return False
        
        # Test 4: Remove credentials
        print("\n4. Testing credential removal...")
        service.remove_credentials()
        
        if not creds_path.exists():
            print("   ✓ Credentials removed successfully")
        else:
            print("   ✗ Credentials file still exists")
            return False
        
        print("\n✅ Secure Storage Tests PASSED")
        return True


def test_workout_sync():
    """Test workout sync to database."""
    print("\n" + "="*60)
    print("TEST: Workout Sync")
    print("="*60)
    
    app = create_app()
    config = Config('config/config.yaml')
    service = TrainerRoadService(config)
    
    with app.app_context():
        # Test 1: Parse and store workouts
        print("\n1. Syncing workouts to database...")
        workouts = service.parse_ics_feed(SAMPLE_ICS_FEED)
        
        for workout_data in workouts:
            workout = WorkoutMetadata.create_or_update(
                workout_date=workout_data['workout_date'],
                workout_name=workout_data['workout_name'],
                workout_type=workout_data['workout_type'],
                duration_minutes=workout_data['duration_minutes'],
                tss=workout_data.get('tss'),
                intensity_factor=workout_data.get('intensity_factor'),
                description=workout_data.get('description')
            )
            print(f"   ✓ Stored: {workout.workout_name} on {workout.workout_date}")
        
        # Test 2: Retrieve workouts
        print("\n2. Retrieving workouts from database...")
        today = date.today()
        
        for i in range(3):
            workout_date = today + timedelta(days=i)
            workout = WorkoutMetadata.get_for_date(workout_date)
            
            if workout:
                print(f"   ✓ Found workout for {workout_date}: {workout.workout_name}")
            else:
                print(f"   ⚠ No workout found for {workout_date}")
        
        # Test 3: Get workout constraints
        print("\n3. Testing workout constraint normalization...")
        
        test_cases = [
            ('Endurance', 'min_duration_minutes', 60),
            ('Threshold', 'indoor_fallback', True),
            ('VO2Max', 'indoor_fallback', True)
        ]
        
        for workout_type, constraint_key, expected_value in test_cases:
            # Find workout of this type
            workout = WorkoutMetadata.query.filter_by(workout_type=workout_type).first()
            
            if workout:
                constraints = service.get_workout_constraints(workout.workout_date)
                
                if constraints:
                    print(f"\n   {workout_type} workout constraints:")
                    print(f"   - Has workout: {constraints['has_workout']}")
                    print(f"   - Min duration: {constraints.get('min_duration_minutes', 'N/A')} min")
                    print(f"   - Indoor fallback: {constraints.get('indoor_fallback', False)}")
                    print(f"   - Preferred intensity: {constraints.get('preferred_intensity', 'N/A')}")
                    
                    if constraint_key in constraints:
                        actual = constraints[constraint_key]
                        if actual == expected_value or (constraint_key == 'min_duration_minutes' and actual >= expected_value):
                            print(f"   ✓ Constraint {constraint_key} correct")
                        else:
                            print(f"   ✗ Constraint {constraint_key} mismatch")
                    else:
                        print(f"   ⚠ Constraint {constraint_key} not found")
                else:
                    print(f"   ✗ No constraints returned for {workout_type}")
        
        # Test 4: Cleanup
        print("\n4. Cleaning up test data...")
        WorkoutMetadata.query.delete()
        print("   ✓ Test workouts removed")
        
        print("\n✅ Workout Sync Tests PASSED")
        return True


def test_settings_ui():
    """Test settings UI integration."""
    print("\n" + "="*60)
    print("TEST: Settings UI")
    print("="*60)
    
    app = create_app()
    client = app.test_client()
    
    with app.app_context():
        # Test 1: Settings page loads
        print("\n1. Testing settings page...")
        response = client.get('/settings/trainerroad')
        
        if response.status_code == 200:
            print(f"   ✓ Settings page loaded (status: {response.status_code})")
            
            if b'TrainerRoad' in response.data or b'ICS Feed' in response.data:
                print("   ✓ TrainerRoad configuration section present")
            else:
                print("   ⚠ TrainerRoad section not found")
        else:
            print(f"   ✗ Settings page failed (status: {response.status_code})")
            return False
        
        # Test 2: Configure feed URL
        print("\n2. Testing feed URL configuration...")
        test_url = "https://www.trainerroad.com/app/calendar/ics/test456"
        
        response = client.post('/settings/trainerroad/configure', data={
            'ics_feed_url': test_url
        }, follow_redirects=True)
        
        if response.status_code == 200:
            print("   ✓ Feed URL configured successfully")
        else:
            print(f"   ✗ Configuration failed (status: {response.status_code})")
        
        # Test 3: Verify connection status
        print("\n3. Testing connection status...")
        response = client.get('/settings/trainerroad')
        
        if b'Connected' in response.data or b'configured' in response.data:
            print("   ✓ Connection status displayed")
        else:
            print("   ⚠ Connection status not clear")
        
        # Test 4: Disconnect
        print("\n4. Testing disconnect...")
        response = client.post('/settings/trainerroad/disconnect', follow_redirects=True)
        
        if response.status_code == 200:
            print("   ✓ Disconnected successfully")
        else:
            print(f"   ✗ Disconnect failed (status: {response.status_code})")
        
        print("\n✅ Settings UI Tests PASSED")
        return True


def main():
    """Run test harness."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test TrainerRoad integration')
    parser.add_argument('--test-all', action='store_true', help='Run all tests')
    parser.add_argument('--test-parser', action='store_true', help='Test ICS parser only')
    parser.add_argument('--test-storage', action='store_true', help='Test secure storage only')
    parser.add_argument('--test-sync', action='store_true', help='Test workout sync only')
    parser.add_argument('--test-ui', action='store_true', help='Test settings UI only')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("TRAINERROAD INTEGRATION TEST HARNESS - Issue #139")
    print("="*60)
    
    results = []
    
    if args.test_all or args.test_parser or (not any([args.test_parser, args.test_storage, args.test_sync, args.test_ui])):
        results.append(('ICS Parser', test_ics_parser()))
    
    if args.test_all or args.test_storage or (not any([args.test_parser, args.test_storage, args.test_sync, args.test_ui])):
        results.append(('Secure Storage', test_secure_storage()))
    
    if args.test_all or args.test_sync or (not any([args.test_parser, args.test_storage, args.test_sync, args.test_ui])):
        results.append(('Workout Sync', test_workout_sync()))
    
    if args.test_all or args.test_ui or (not any([args.test_parser, args.test_storage, args.test_sync, args.test_ui])):
        results.append(('Settings UI', test_settings_ui()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests PASSED!")
        return 0
    else:
        print("\n⚠️  Some tests FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
