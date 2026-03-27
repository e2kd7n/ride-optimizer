#!/usr/bin/env python3
"""
Manually create a rate limit block file to prevent geocoding attempts.

This is useful when you know you're rate limited by Nominatim but the system
hasn't detected it yet (e.g., if geocoding was interrupted before the rate
limit detection could create the file).

Usage:
    python3 scripts/set_rate_limit_block.py [hours]

Arguments:
    hours: Number of hours to block (default: 4)

Examples:
    python3 scripts/set_rate_limit_block.py      # Block for 4 hours
    python3 scripts/set_rate_limit_block.py 2    # Block for 2 hours
    python3 scripts/set_rate_limit_block.py 24   # Block for 24 hours
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def create_rate_limit_block(hours: int = 4) -> None:
    """Create a rate limit block file."""
    cache_dir = Path(__file__).parent.parent / 'cache'
    cache_dir.mkdir(exist_ok=True)
    
    rate_limit_file = cache_dir / 'geocoding_rate_limit.json'
    
    now = datetime.now()
    blocked_until = now + timedelta(hours=hours)
    
    data = {
        'blocked_until': blocked_until.isoformat(),
        'blocked_at': now.isoformat(),
        'reason': 'Manual block - IP rate limited by Nominatim',
        'note': f'User-created to prevent further rate limiting for {hours} hours'
    }
    
    with open(rate_limit_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Get timezone name for display
    try:
        import time
        tz_name = time.tzname[time.daylight]
    except:
        tz_name = 'local time'
    
    print("=" * 60)
    print("✅ Rate Limit Block Created")
    print("=" * 60)
    print(f"Blocked until: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}")
    print(f"Duration: {hours} hours")
    print()
    print("Next time you run analysis, geocoding will be skipped.")
    print("The block will automatically expire after the time above.")
    print("=" * 60)


def main():
    """Main entry point."""
    hours = 4  # Default
    
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
            if hours <= 0:
                print("Error: Hours must be positive")
                sys.exit(1)
        except ValueError:
            print(f"Error: Invalid hours value: {sys.argv[1]}")
            print("Usage: python3 scripts/set_rate_limit_block.py [hours]")
            sys.exit(1)
    
    create_rate_limit_block(hours)


if __name__ == '__main__':
    main()

# Made with Bob
