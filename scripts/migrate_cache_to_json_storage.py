#!/usr/bin/env python3
"""
Migrate cached data from old format to new Smart Static JSON storage format.

This script converts:
- cache/route_groups_cache.json → data/route_groups.json
- Old database tables → JSON files in data/

Run this once to migrate existing data to the new Smart Static architecture.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrate_route_groups():
    """Migrate route groups from cache to data directory."""
    old_file = Path('cache/route_groups_cache.json')
    new_file = Path('data/route_groups.json')
    
    if not old_file.exists():
        logger.warning(f"Old cache file not found: {old_file}")
        return False
    
    logger.info(f"Migrating route groups from {old_file} to {new_file}...")
    
    try:
        # Load old format
        with open(old_file, 'r') as f:
            old_data = json.load(f)
        
        # Convert to new format
        new_data = {
            'route_groups': old_data.get('groups', []),
            'activity_ids': old_data.get('activity_ids', []),
            'similarity_threshold': old_data.get('similarity_threshold', 0.85),
            'algorithm': old_data.get('algorithm', 'frechet'),
            'updated_at': old_data.get('timestamp', datetime.now().isoformat())
        }
        
        # Ensure data directory exists
        new_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write new format
        with open(new_file, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        # Set secure permissions
        new_file.chmod(0o600)
        
        logger.info(f"✅ Migrated {len(new_data['route_groups'])} route groups")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate route groups: {e}")
        return False


def create_analysis_status():
    """Create analysis status file from migrated data."""
    route_groups_file = Path('data/route_groups.json')
    status_file = Path('data/analysis_status.json')
    
    if not route_groups_file.exists():
        logger.warning("No route groups data found, skipping status creation")
        return False
    
    logger.info("Creating analysis status file...")
    
    try:
        # Load route groups to count
        with open(route_groups_file, 'r') as f:
            route_data = json.load(f)
        
        # Create status
        status = {
            'last_analysis': route_data.get('updated_at', datetime.now().isoformat()),
            'activities_count': len(route_data.get('activity_ids', [])),
            'route_groups_count': len(route_data.get('route_groups', [])),
            'long_rides_count': 0,  # Will be populated when long rides are migrated
            'has_data': len(route_data.get('route_groups', [])) > 0
        }
        
        # Write status
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        # Set secure permissions
        status_file.chmod(0o600)
        
        logger.info(f"✅ Created analysis status: {status['activities_count']} activities, {status['route_groups_count']} route groups")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create analysis status: {e}")
        return False


def migrate_favorites():
    """Create empty favorites file if it doesn't exist."""
    favorites_file = Path('data/favorite_routes.json')
    
    if favorites_file.exists():
        logger.info("Favorites file already exists, skipping")
        return True
    
    logger.info("Creating empty favorites file...")
    
    try:
        favorites_data = {
            'favorites': [],
            'updated_at': datetime.now().isoformat()
        }
        
        # Ensure directory exists
        favorites_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(favorites_file, 'w') as f:
            json.dump(favorites_data, f, indent=2)
        
        # Set secure permissions
        favorites_file.chmod(0o600)
        
        logger.info("✅ Created empty favorites file")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create favorites file: {e}")
        return False


def main():
    """Run all migrations."""
    logger.info("=" * 60)
    logger.info("Smart Static Architecture - Cache Migration")
    logger.info("=" * 60)
    
    results = []
    
    # Migrate route groups
    results.append(("Route Groups", migrate_route_groups()))
    
    # Create analysis status
    results.append(("Analysis Status", create_analysis_status()))
    
    # Create favorites file
    results.append(("Favorites", migrate_favorites()))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    
    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{name}: {status}")
    
    all_success = all(success for _, success in results)
    
    if all_success:
        logger.info("\n🎉 All migrations completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Restart the API server: python3 launch.py")
        logger.info("2. Refresh the dashboard in your browser")
        logger.info("3. You should now see your routes and statistics!")
        return 0
    else:
        logger.error("\n⚠️  Some migrations failed. Check the errors above.")
        return 1


if __name__ == '__main__':
    exit(main())


# Made with Bob