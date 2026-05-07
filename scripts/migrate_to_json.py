#!/usr/bin/env python3
"""
Migration script: SQLite → JSON files

Converts data from SQLAlchemy/SQLite database to JSON file storage
for the Smart Static architecture.

Usage:
    python scripts/migrate_to_json.py [--dry-run] [--backup]
"""

import sys
import os
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.json_storage import JSONStorage
from src.config import Config

# Try to import SQLAlchemy models (may fail if already migrated)
try:
    from app.models import db, FavoriteRoute
    from app.models.weather import WeatherSnapshot
    from app import create_app
    SQLALCHEMY_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import SQLAlchemy models: {e}")
    SQLALCHEMY_AVAILABLE = False


def backup_database(db_path: Path, backup_dir: Path):
    """
    Create backup of SQLite database.
    
    Args:
        db_path: Path to database file
        backup_dir: Directory for backups
    """
    if not db_path.exists():
        print(f"No database file found at {db_path}")
        return None
    
    backup_dir.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"ride_optimizer_backup_{timestamp}.db"
    
    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def migrate_favorites(storage: JSONStorage, dry_run: bool = False) -> dict:
    """
    Migrate favorites from SQLite to JSON.
    
    Args:
        storage: JSONStorage instance
        dry_run: If True, don't write files
        
    Returns:
        Migration statistics
    """
    print("\n=== Migrating Favorites ===")
    
    if not SQLALCHEMY_AVAILABLE:
        print("SQLAlchemy not available, skipping favorites migration")
        return {'migrated': 0, 'errors': 0}
    
    try:
        app = create_app('production')
        with app.app_context():
            favorites = FavoriteRoute.query.all()
            
            if not favorites:
                print("No favorites found in database")
                return {'migrated': 0, 'errors': 0}
            
            # Convert to JSON structure
            favorites_data = {
                'routes': [fav.route_id for fav in favorites],
                'updated_at': datetime.now().isoformat(),
                'migrated_from_sqlite': True,
                'migration_date': datetime.now().isoformat()
            }
            
            print(f"Found {len(favorites)} favorites")
            
            if dry_run:
                print("DRY RUN: Would write to favorites.json:")
                print(json.dumps(favorites_data, indent=2))
            else:
                success = storage.write('favorites.json', favorites_data)
                if success:
                    print(f"✓ Migrated {len(favorites)} favorites to favorites.json")
                else:
                    print("✗ Failed to write favorites.json")
                    return {'migrated': 0, 'errors': 1}
            
            return {'migrated': len(favorites), 'errors': 0}
            
    except Exception as e:
        print(f"✗ Error migrating favorites: {e}")
        return {'migrated': 0, 'errors': 1}


def migrate_weather(storage: JSONStorage, dry_run: bool = False) -> dict:
    """
    Migrate weather snapshots from SQLite to JSON.
    
    Args:
        storage: JSONStorage instance
        dry_run: If True, don't write files
        
    Returns:
        Migration statistics
    """
    print("\n=== Migrating Weather Data ===")
    
    if not SQLALCHEMY_AVAILABLE:
        print("SQLAlchemy not available, skipping weather migration")
        return {'migrated': 0, 'errors': 0}
    
    try:
        app = create_app('production')
        with app.app_context():
            # Get recent weather snapshots (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            snapshots = WeatherSnapshot.query.filter(
                WeatherSnapshot.timestamp >= cutoff,
                WeatherSnapshot.is_current == True
            ).all()
            
            if not snapshots:
                print("No recent weather snapshots found in database")
                return {'migrated': 0, 'errors': 0}
            
            # Convert to JSON structure
            weather_cache = {'locations': {}}
            
            for snapshot in snapshots:
                cache_key = f"{snapshot.latitude:.4f}_{snapshot.longitude:.4f}"
                
                weather_cache['locations'][cache_key] = {
                    'weather_data': {
                        'temperature_c': snapshot.temperature_c,
                        'temperature_f': snapshot.temperature_c * 9/5 + 32 if snapshot.temperature_c else None,
                        'conditions': snapshot.conditions,
                        'wind_speed_kph': snapshot.wind_speed_kph,
                        'wind_direction_degrees': snapshot.wind_direction_deg,
                        'precipitation_mm': snapshot.precipitation_mm,
                        'humidity_pct': snapshot.humidity_pct,
                        'comfort_score': snapshot.comfort_score,
                        'cycling_favorability': snapshot.cycling_favorability
                    },
                    'timestamp': snapshot.timestamp.isoformat(),
                    'location_name': snapshot.location_name
                }
            
            print(f"Found {len(snapshots)} weather snapshots")
            
            if dry_run:
                print("DRY RUN: Would write to weather_cache.json:")
                print(f"Locations: {len(weather_cache['locations'])}")
            else:
                success = storage.write('weather_cache.json', weather_cache)
                if success:
                    print(f"✓ Migrated {len(snapshots)} weather snapshots to weather_cache.json")
                else:
                    print("✗ Failed to write weather_cache.json")
                    return {'migrated': 0, 'errors': 1}
            
            return {'migrated': len(snapshots), 'errors': 0}
            
    except Exception as e:
        print(f"✗ Error migrating weather data: {e}")
        import traceback
        traceback.print_exc()
        return {'migrated': 0, 'errors': 1}


def create_initial_json_files(storage: JSONStorage, dry_run: bool = False):
    """
    Create initial JSON file structure if files don't exist.
    
    Args:
        storage: JSONStorage instance
        dry_run: If True, don't write files
    """
    print("\n=== Creating Initial JSON Files ===")
    
    files_to_create = {
        'status.json': {
            'has_data': False,
            'last_analysis': None,
            'activities_count': 0,
            'route_groups_count': 0,
            'long_rides_count': 0,
            'created_at': datetime.now().isoformat()
        },
        'recommendations.json': {
            'current': None,
            'alternatives': [],
            'updated_at': None
        },
        'routes.json': {
            'commute_routes': [],
            'long_rides': [],
            'updated_at': None
        }
    }
    
    for filename, default_data in files_to_create.items():
        if not storage.exists(filename):
            if dry_run:
                print(f"DRY RUN: Would create {filename}")
            else:
                success = storage.write(filename, default_data)
                if success:
                    print(f"✓ Created {filename}")
                else:
                    print(f"✗ Failed to create {filename}")
        else:
            print(f"  {filename} already exists, skipping")


def verify_migration(storage: JSONStorage) -> bool:
    """
    Verify migration was successful.
    
    Args:
        storage: JSONStorage instance
        
    Returns:
        True if verification passed
    """
    print("\n=== Verifying Migration ===")
    
    required_files = ['favorites.json', 'weather_cache.json', 'status.json']
    all_exist = True
    
    for filename in required_files:
        if storage.exists(filename):
            data = storage.read(filename)
            if data:
                print(f"✓ {filename} exists and is readable")
            else:
                print(f"✗ {filename} exists but is empty or unreadable")
                all_exist = False
        else:
            print(f"✗ {filename} does not exist")
            all_exist = False
    
    return all_exist


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description='Migrate SQLite database to JSON files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without writing files'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of database before migration'
    )
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Directory for JSON files (default: data)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Ride Optimizer: SQLite → JSON Migration")
    print("=" * 60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")
    
    # Initialize storage
    storage = JSONStorage(data_dir=args.data_dir)
    
    # Backup database if requested
    if args.backup and not args.dry_run:
        db_path = Path('data/ride_optimizer.db')
        backup_dir = Path('backups')
        backup_database(db_path, backup_dir)
    
    # Run migrations
    stats = {
        'favorites': migrate_favorites(storage, args.dry_run),
        'weather': migrate_weather(storage, args.dry_run)
    }
    
    # Create initial JSON files
    create_initial_json_files(storage, args.dry_run)
    
    # Verify migration
    if not args.dry_run:
        success = verify_migration(storage)
    else:
        success = True
    
    # Print summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Favorites migrated: {stats['favorites']['migrated']}")
    print(f"Weather snapshots migrated: {stats['weather']['migrated']}")
    print(f"Total errors: {stats['favorites']['errors'] + stats['weather']['errors']}")
    
    if success and not args.dry_run:
        print("\n✓ Migration completed successfully!")
        print(f"\nJSON files created in: {storage.data_dir}")
        return 0
    elif args.dry_run:
        print("\n✓ Dry run completed - no files were modified")
        return 0
    else:
        print("\n✗ Migration completed with errors")
        return 1


if __name__ == '__main__':
    sys.exit(main())


# Made with Bob