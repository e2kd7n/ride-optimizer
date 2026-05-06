# Database Models Documentation

SQLite-backed persistence layer for the Ride Optimizer web platform.

## Architecture

### Hybrid Persistence Model

The system uses a **hybrid persistence approach**:

1. **SQLite Database**: Structured metadata and summaries
   - Analysis snapshots
   - Route summaries
   - User preferences
   - Job history
   - Workout metadata

2. **File Caches**: Heavy artifacts
   - Full route coordinates (polylines)
   - Complete activity details
   - Weather forecast data
   - Geocoding results

### Why Hybrid?

- **Performance**: Avoid storing large blobs in SQLite
- **Simplicity**: No need for complex blob management
- **Flexibility**: File caches can be cleared independently
- **Compatibility**: Existing cache system continues to work

## Models

### AnalysisSnapshot

Stores metadata about analysis runs.

**Purpose**: Enable dashboard rendering without re-running full analysis.

**Fields**:
- `analysis_date`: When analysis was performed
- `status`: 'success', 'error', 'in_progress'
- `activities_count`, `route_groups_count`, `long_rides_count`: Data counts
- `home_lat/lon/name`, `work_lat/lon/name`: Location info
- `strava_last_sync`, `weather_last_sync`: Freshness indicators
- `geocoding_complete`: Geocoding status
- `analysis_duration_seconds`: Performance metric

**Relationships**:
- One-to-many with RouteGroup
- One-to-many with LongRide

**Key Methods**:
```python
# Get latest successful analysis
snapshot = AnalysisSnapshot.get_latest()

# Check if data is stale
if AnalysisSnapshot.is_stale(hours=24):
    # Trigger new analysis
    pass
```

### RouteGroup

Stores summary information about commute route groups.

**Purpose**: Quick access to route metadata without loading full coordinates.

**Fields**:
- `group_id`: Unique identifier (e.g., "home_to_work_1")
- `name`: Human-readable name
- `direction`: "home_to_work" or "work_to_home"
- `frequency`: Number of times used
- `avg_distance`, `avg_duration`, `avg_elevation`, `avg_speed`: Statistics
- `is_plus_route`: Whether this is a "plus route" variant
- `consistency_score`: Route consistency (0-1)
- `is_favorite`: User favorite flag
- `notes`: User notes

**Data Ownership**:
- **In Database**: Summary statistics, metadata
- **In File Cache**: Full route coordinates, individual route details

### LongRide

Stores summary information about long/recreational rides.

**Purpose**: Quick access to ride metadata for browsing and recommendations.

**Fields**:
- `activity_id`: Strava activity ID
- `name`: Ride name
- `ride_type`: 'Ride', 'GravelRide', etc.
- `distance`, `duration`, `elevation_gain`, `average_speed`: Statistics
- `start_lat/lon`, `end_lat/lon`: Location info
- `is_loop`: Whether ride is a loop
- `uses`: Number of times ridden
- `last_ridden`: Last ride date
- `is_favorite`: User favorite flag
- `notes`, `tags`: User annotations

**Data Ownership**:
- **In Database**: Summary statistics, metadata
- **In File Cache**: Full route coordinates

### UserPreference

Stores user settings and configuration.

**Purpose**: Persist user preferences across sessions.

**Structure**: Key-value store with categories
- `category`: 'weather', 'routes', 'notifications', 'analysis'
- `key`: Preference key
- `value`: JSON-encoded value

**Categories**:

**Weather**:
- `temperature_unit`: 'F' or 'C'
- `wind_speed_unit`: 'mph' or 'kph'
- `max_wind_speed`: Maximum acceptable wind
- `max_precipitation`: Maximum acceptable rain
- `min_temperature`, `max_temperature`: Temperature range

**Routes**:
- `commute_min_distance`, `commute_max_distance`: Commute distance range
- `long_ride_min_distance`, `long_ride_max_distance`: Long ride distance range
- `prefer_variety`: Prefer less-used routes

**Notifications**:
- `email_enabled`: Enable email notifications
- `new_commute_recommendation`: Notify on new commute recommendation
- `new_long_ride_recommendation`: Notify on new long ride recommendation
- `data_sync_complete`, `data_sync_error`: Sync notifications

**Analysis**:
- `auto_sync_interval`: Auto-sync interval in seconds
- `cache_ttl`: Cache time-to-live
- `enable_weather`, `enable_geocoding`: Feature flags

**Key Methods**:
```python
# Get a preference
value = UserPreference.get('weather', 'temperature_unit', default='F')

# Set a preference
UserPreference.set('weather', 'temperature_unit', 'C')

# Get all preferences in a category
weather_prefs = UserPreference.get_category('weather')

# Set defaults
UserPreference.set_defaults()
```

### JobHistory

Tracks background job execution for monitoring and debugging.

**Purpose**: Support Issue #137 (Scheduled Jobs and Status Tracking).

**Fields**:
- `job_id`: Unique job identifier
- `job_type`: 'analysis', 'sync', 'geocoding', etc.
- `job_name`: Human-readable name
- `status`: 'queued', 'running', 'completed', 'failed', 'cancelled'
- `progress`: Progress value (0.0 to 1.0)
- `queued_at`, `started_at`, `completed_at`: Timing
- `duration_seconds`: Execution duration
- `result_summary`: JSON-encoded results
- `error_message`, `error_traceback`: Error details
- `parameters`: JSON-encoded job parameters
- `triggered_by`: 'user', 'schedule', 'system'

**Key Methods**:
```python
# Create a new job
job = JobHistory.create_job('analysis', 'Full Analysis', triggered_by='user')

# Update job status
job.start()
job.update_progress(0.5, "Processing routes...")
job.complete({'routes': 10, 'rides': 5})

# Or mark as failed
job.fail("Error message", traceback_str)

# Get recent jobs
recent = JobHistory.get_recent(limit=50, job_type='analysis')

# Cleanup old jobs
deleted = JobHistory.cleanup_old(days=30)
```

### WorkoutMetadata

Stores TrainerRoad workout information and fit analysis.

**Purpose**: Support workout-fit recommendations without re-fetching from TrainerRoad.

**Fields**:
- `workout_id`: TrainerRoad workout ID
- `workout_name`: Workout name
- `workout_date`: Scheduled date
- `workout_type`: 'Endurance', 'Threshold', 'VO2Max', etc.
- `duration_minutes`: Workout duration
- `tss`: Training Stress Score
- `intensity_factor`: Intensity Factor
- `status`: 'scheduled', 'completed', 'skipped'
- `completed_at`: Completion timestamp
- `fit_score`: How well commute fits workout (0-1)
- `fit_reason`: Explanation of fit score
- `recommended_route_id`: Best route for this workout
- `synced_at`: Last sync from TrainerRoad

**Key Methods**:
```python
# Get upcoming workouts
workouts = WorkoutMetadata.get_upcoming(days=7)

# Get workout for specific date
workout = WorkoutMetadata.get_for_date(date.today())

# Sync from TrainerRoad
count = WorkoutMetadata.sync_from_trainerroad(workouts_data)

# Calculate fit for routes
best_route, score = workout.calculate_fit(route_groups)
```

## Database Initialization

### Setup

```python
from flask import Flask
from app.models import db, init_db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/ride_optimizer.db'

# Initialize database
init_db(app)
```

### Migrations

For now, we use simple `create_all()` approach. Future: Alembic migrations.

```python
from app.models import db

# Create all tables
with app.app_context():
    db.create_all()

# Reset database (WARNING: deletes all data!)
from app.models import reset_db
reset_db(app)
```

## Usage Examples

### Storing Analysis Results

```python
from app.models import AnalysisSnapshot, RouteGroup, LongRide, db

# Create snapshot
snapshot = AnalysisSnapshot(
    status='success',
    activities_count=150,
    route_groups_count=5,
    long_rides_count=20,
    home_lat=41.8781,
    home_lon=-87.6298,
    home_name='Home',
    work_lat=41.8819,
    work_lon=-87.6278,
    work_name='Work',
    geocoding_complete=True,
    analysis_duration_seconds=45.2
)
db.session.add(snapshot)
db.session.commit()

# Add route groups
for group in route_groups:
    rg = RouteGroup(
        snapshot_id=snapshot.id,
        group_id=group.id,
        name=group.name,
        direction=group.direction,
        frequency=group.frequency,
        avg_distance=group.representative_route.distance,
        avg_duration=group.representative_route.duration,
        avg_elevation=group.representative_route.elevation_gain,
        avg_speed=group.representative_route.average_speed,
        is_plus_route=group.is_plus_route
    )
    db.session.add(rg)

db.session.commit()
```

### Querying Data

```python
# Get latest analysis
snapshot = AnalysisSnapshot.get_latest()

# Get all route groups from latest analysis
route_groups = RouteGroup.query.filter_by(snapshot_id=snapshot.id).all()

# Get favorite routes
favorites = RouteGroup.query.filter_by(is_favorite=True).all()

# Get long rides sorted by distance
long_rides = LongRide.query.order_by(LongRide.distance.desc()).limit(10).all()

# Search routes by name
routes = RouteGroup.query.filter(RouteGroup.name.like('%Harrison%')).all()
```

### Managing Preferences

```python
from app.models import UserPreference

# Set defaults on first run
UserPreference.set_defaults()

# Get temperature unit
temp_unit = UserPreference.get('weather', 'temperature_unit')

# Update preference
UserPreference.set('weather', 'max_wind_speed', 25)

# Get all weather preferences
weather_prefs = UserPreference.get_category('weather')
```

### Tracking Jobs

```python
from app.models import JobHistory

# Create and track a job
job = JobHistory.create_job('analysis', 'Full Route Analysis')

try:
    job.start()
    
    # Do work...
    job.update_progress(0.3, "Fetching activities...")
    # More work...
    job.update_progress(0.7, "Analyzing routes...")
    # Final work...
    
    job.complete({'routes': 10, 'activities': 150})
except Exception as e:
    job.fail(str(e), traceback.format_exc())
```

## Database Schema

```sql
-- Analysis Snapshots
CREATE TABLE analysis_snapshots (
    id INTEGER PRIMARY KEY,
    analysis_date DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    activities_count INTEGER DEFAULT 0,
    route_groups_count INTEGER DEFAULT 0,
    long_rides_count INTEGER DEFAULT 0,
    home_lat FLOAT,
    home_lon FLOAT,
    home_name VARCHAR(200),
    work_lat FLOAT,
    work_lon FLOAT,
    work_name VARCHAR(200),
    strava_last_sync DATETIME,
    weather_last_sync DATETIME,
    geocoding_complete BOOLEAN DEFAULT 0,
    analysis_duration_seconds FLOAT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Route Groups
CREATE TABLE route_groups (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL,
    group_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    direction VARCHAR(20) NOT NULL,
    frequency INTEGER DEFAULT 0,
    avg_distance FLOAT NOT NULL,
    avg_duration FLOAT NOT NULL,
    avg_elevation FLOAT NOT NULL,
    avg_speed FLOAT NOT NULL,
    is_plus_route BOOLEAN DEFAULT 0,
    consistency_score FLOAT,
    is_favorite BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES analysis_snapshots(id)
);

-- Long Rides
CREATE TABLE long_rides (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL,
    activity_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    ride_type VARCHAR(50),
    distance FLOAT NOT NULL,
    duration INTEGER NOT NULL,
    elevation_gain FLOAT NOT NULL,
    average_speed FLOAT NOT NULL,
    start_lat FLOAT,
    start_lon FLOAT,
    end_lat FLOAT,
    end_lon FLOAT,
    is_loop BOOLEAN DEFAULT 0,
    uses INTEGER DEFAULT 1,
    last_ridden DATETIME,
    is_favorite BOOLEAN DEFAULT 0,
    notes TEXT,
    tags VARCHAR(500),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES analysis_snapshots(id)
);

-- User Preferences
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    description VARCHAR(500),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE (category, key)
);

-- Job History
CREATE TABLE job_history (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(100) NOT NULL UNIQUE,
    job_type VARCHAR(50) NOT NULL,
    job_name VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL,
    progress FLOAT DEFAULT 0.0,
    queued_at DATETIME NOT NULL,
    started_at DATETIME,
    completed_at DATETIME,
    duration_seconds FLOAT,
    result_summary TEXT,
    error_message TEXT,
    error_traceback TEXT,
    parameters TEXT,
    triggered_by VARCHAR(50),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- Workout Metadata
CREATE TABLE workout_metadata (
    id INTEGER PRIMARY KEY,
    workout_id VARCHAR(100) NOT NULL UNIQUE,
    workout_name VARCHAR(200) NOT NULL,
    workout_date DATE NOT NULL,
    workout_type VARCHAR(50),
    duration_minutes INTEGER,
    tss FLOAT,
    intensity_factor FLOAT,
    status VARCHAR(20) DEFAULT 'scheduled',
    completed_at DATETIME,
    fit_score FLOAT,
    fit_reason TEXT,
    recommended_route_id VARCHAR(100),
    notes TEXT,
    synced_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

## Best Practices

1. **Always use sessions**: Commit changes explicitly
2. **Handle errors**: Wrap database operations in try/except
3. **Use relationships**: Leverage SQLAlchemy relationships for cleaner code
4. **Index appropriately**: Key fields are already indexed
5. **Clean up old data**: Use cleanup methods for job history
6. **Validate data**: Check data before inserting
7. **Use transactions**: Group related operations

## Future Enhancements

1. **Alembic Migrations**: Proper schema versioning
2. **Soft Deletes**: Add deleted_at field instead of hard deletes
3. **Audit Trail**: Track who changed what and when
4. **Full-text Search**: Add FTS for route name search
5. **Caching**: Add Redis for frequently accessed data
6. **Replication**: Support read replicas for scaling