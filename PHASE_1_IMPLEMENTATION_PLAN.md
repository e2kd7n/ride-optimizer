no# Phase 1: Foundation Migration - Implementation Plan

**Timeline:** Week 1 (5 days)  
**Status:** 🚀 ACTIVE  
**Owner:** Foundation Squad

---

## Current Architecture Analysis

### Services Status (✅ = Already Flask-independent)
- ✅ `analysis_service.py` - No Flask dependencies, returns dicts
- ✅ `commute_service.py` - No Flask dependencies, returns dicts
- ✅ `weather_service.py` - No Flask dependencies, returns dicts
- ✅ `planner_service.py` - No Flask dependencies, returns dicts
- ⚠️ `route_library_service.py` - Uses SQLAlchemy for favorites only
- ⚠️ `trainerroad_service.py` - Need to check

### Database Dependencies
- `app/models/weather.py` - WeatherSnapshot (SQLAlchemy)
- `app/models/__init__.py` - FavoriteRoute (SQLAlchemy)
- `app/models/workouts.py` - WorkoutMetadata (SQLAlchemy)

### Key Insight
**Services are already 90% Flask-independent!** They return plain Python dicts, not Flask responses. This accelerates our timeline significantly.

---

## Task 1.1: Extract Service Layer (SIMPLIFIED - 1 day instead of 2)

### What Needs to Change
1. **Remove SQLAlchemy from route_library_service.py**
   - Replace `FavoriteRoute` model with JSON file storage
   - Update `_load_favorites()` to read from JSON
   - Update `toggle_favorite()` to write to JSON

2. **Remove SQLAlchemy from weather_service.py**
   - Replace `WeatherSnapshot` model with JSON file storage
   - Update caching logic to use JSON files
   - Preserve 2-hour fresh / 24-hour stale logic

3. **Check trainerroad_service.py**
   - Verify no Flask dependencies
   - Update if needed

### Implementation Steps

#### Step 1: Create JSON Storage Utilities (2 hours)
**File:** `src/json_storage.py`

```python
"""
JSON file storage utilities for Smart Static architecture.

Provides atomic writes, file locking, and proper permissions.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import fcntl
from datetime import datetime

class JSONStorage:
    """Thread-safe JSON file storage with atomic writes."""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, mode=0o700)
    
    def read(self, filename: str, default: Any = None) -> Any:
        """Read JSON file with file locking."""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            return default
        
        try:
            with open(filepath, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            return default
    
    def write(self, filename: str, data: Any):
        """Write JSON file atomically with proper permissions."""
        filepath = self.data_dir / filename
        temp_path = filepath.with_suffix('.tmp')
        
        try:
            # Write to temp file
            with open(temp_path, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Set permissions
            os.chmod(temp_path, 0o600)
            
            # Atomic rename
            temp_path.replace(filepath)
            
        except Exception as e:
            logger.error(f"Error writing {filename}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
```

#### Step 2: Update route_library_service.py (2 hours)
Replace SQLAlchemy favorites with JSON storage:

```python
# OLD (SQLAlchemy)
from app.models import db, FavoriteRoute

def _load_favorites(self):
    favorites = FavoriteRoute.query.all()
    self._favorites = {fav.route_id for fav in favorites}

# NEW (JSON)
from src.json_storage import JSONStorage

def __init__(self, config: Config):
    self.config = config
    self.storage = JSONStorage()
    self._load_favorites()

def _load_favorites(self):
    data = self.storage.read('favorites.json', default={'routes': []})
    self._favorites = set(data.get('routes', []))

def toggle_favorite(self, route_id: str, is_favorite: bool):
    if is_favorite:
        self._favorites.add(route_id)
    else:
        self._favorites.discard(route_id)
    
    # Save to JSON
    self.storage.write('favorites.json', {
        'routes': list(self._favorites),
        'updated_at': datetime.now().isoformat()
    })
```

#### Step 3: Update weather_service.py (2 hours)
Replace WeatherSnapshot model with JSON storage:

```python
# NEW: Weather cache structure
{
    "locations": {
        "lat_lon_key": {
            "weather_data": {...},
            "timestamp": "2026-05-07T03:00:00Z",
            "location_name": "Home"
        }
    }
}

def get_current_weather(self, lat: float, lon: float, location_name: Optional[str] = None):
    cache_key = f"{lat:.4f}_{lon:.4f}"
    cache = self.storage.read('weather_cache.json', default={'locations': {}})
    
    # Check cache (2-hour fresh window)
    if cache_key in cache['locations']:
        cached = cache['locations'][cache_key]
        timestamp = datetime.fromisoformat(cached['timestamp'])
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600
        
        if age_hours < 2:
            logger.info(f"Using cached weather, age: {age_hours:.1f}h")
            return cached['weather_data']
    
    # Fetch fresh data...
    # Store in cache...
```

---

## Task 1.2: Create Minimal API (1 day)

### API Specification

**File:** `api.py` (root directory, 50-100 lines)

```python
"""
Minimal Flask API for Smart Static architecture.

Provides 4 JSON endpoints for static HTML pages to fetch data.
No sessions, CORS, rate limiting - optimized for single-user Pi deployment.
"""
from flask import Flask, jsonify, send_from_directory
from pathlib import Path
import logging

from src.config import Config
from app.services.analysis_service import AnalysisService
