#!/usr/bin/env python3
"""
Test script for scheduler integration.
Verifies that the scheduler initializes and integrates with Flask app.
"""

import sys
from app import create_app

def test_scheduler_integration():
    """Test that scheduler integrates properly with Flask app."""
    print("Testing scheduler integration...")
    
    try:
        # Create Flask app
        print("1. Creating Flask app...")
        app = create_app('development')
        print("   ✓ Flask app created successfully")
        
        # The scheduler starts automatically in create_app
        # We can verify it's working via the API endpoints
        print("2. Verifying scheduler via API...")
        
        # Test health check
        print("3. Testing health check...")
        with app.app_context():
            from app.scheduler import HealthChecker
            health_checker = HealthChecker()
            health = health_checker.check_all()
            print(f"   Overall status: {health.overall_status}")
            print(f"   Checks passed: {health.checks_passed}/{len(health.checks)}")
            if health.warnings:
                print("   Warnings:")
                for warning in health.warnings:
                    print(f"   - {warning}")
        print("   ✓ Health check completed")
        
        # Test API endpoints
        print("4. Testing API endpoints...")
        with app.test_client() as client:
            # Test /api/health
            response = client.get('/api/health')
            if response.status_code != 200:
                print(f"   ✗ /api/health returned {response.status_code}")
                return False
            print("   ✓ /api/health endpoint working")
            
            # Test /api/status
            response = client.get('/api/status')
            if response.status_code != 200:
                print(f"   ✗ /api/status returned {response.status_code}")
                return False
            print("   ✓ /api/status endpoint working")
            
            # Test /api/scheduler/jobs
            response = client.get('/api/scheduler/jobs')
            if response.status_code != 200:
                print(f"   ✗ /api/scheduler/jobs returned {response.status_code}")
                return False
            data = response.get_json()
            print(f"   ✓ /api/scheduler/jobs endpoint working ({data['count']} jobs)")
            
            if data['count'] == 0:
                print("   ✗ No jobs found in scheduler")
                return False
            
            print(f"   Jobs found:")
            for job in data.get('jobs', []):
                print(f"   - {job.get('name')} (next run: {job.get('next_run_time')})")
        
        print("\n✅ All tests passed! Scheduler integration successful.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_scheduler_integration()
    sys.exit(0 if success else 1)

# Made with Bob
