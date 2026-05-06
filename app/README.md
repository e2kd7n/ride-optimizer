# Ride Optimizer Web Application

Flask-based web platform for the Ride Optimizer project (v3.0.0).

## Structure

```
app/
├── __init__.py           # Application factory
├── config.py             # Configuration classes
├── routes/               # Route blueprints
│   ├── __init__.py
│   ├── dashboard.py      # Main dashboard
│   ├── commute.py        # Commute recommendations
│   ├── planner.py        # Long ride planner
│   ├── route_library.py  # Route browsing
│   ├── settings.py       # User settings
│   └── api.py            # Internal API
├── templates/            # Jinja2 templates
│   ├── base.html         # Base template
│   ├── dashboard/
│   └── errors/
└── static/               # Static assets
    ├── css/
    └── js/
```

## Running the Application

### Development Mode

```bash
# Using Flask CLI (recommended)
flask run

# Or using Python directly
python wsgi.py

# Or using the WSGI entry point
python -m flask run
```

The application will be available at `http://localhost:5000`

### Production Mode

```bash
# Using Gunicorn (recommended for production)
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# Or using uWSGI
uwsgi --http :5000 --wsgi-file wsgi.py --callable app
```

## Configuration

Configuration is managed through environment-specific classes in `config.py`:

- **DevelopmentConfig**: Debug mode, verbose logging
- **ProductionConfig**: Optimized for production deployment
- **TestingConfig**: For running tests

Set the environment using the `FLASK_ENV` environment variable:

```bash
export FLASK_ENV=development  # or production, testing
```

## Blueprints

### Dashboard (`/`)
- Main landing page
- Quick stats and recommendations
- System status overview

### Commute (`/commute`)
- Next commute recommendations
- Weather and traffic analysis
- Workout fit integration
- Historical performance

### Planner (`/planner`)
- Long ride planning (7-day forecast)
- Route suggestions
- Calendar view
- Weather optimization

### Route Library (`/routes`)
- Browse all routes
- Search and filter
- Route details and statistics
- Route comparison

### Settings (`/settings`)
- Strava integration
- TrainerRoad integration
- Weather preferences
- Route preferences
- Notification settings

### API (`/api`)
- RESTful JSON endpoints
- Health checks
- Background job management
- Cache management
- System metrics

## Templates

Templates use Jinja2 and extend from `base.html`. All templates include:

- Responsive navigation
- Flash message support
- Mobile-friendly design
- Consistent styling

## Static Assets

### CSS (`static/css/main.css`)
- Responsive design
- Mobile-first approach
- CSS variables for theming
- Utility classes

### JavaScript (`static/js/main.js`)
- Mobile menu toggle
- Flash message handling
- AJAX helpers
- Utility functions

## Database

SQLite database configuration (to be implemented in Issue #131):

- Development: `instance/ride_optimizer_dev.db`
- Production: `instance/ride_optimizer.db`
- Testing: In-memory database

## Background Jobs

Background job scheduling (to be implemented in Issue #137):

- Data synchronization
- Geocoding processing
- Weather updates
- Report generation

## Service Layer

Shared business logic (to be implemented in Issue #130):

- Route analysis
- Recommendations engine
- Weather integration
- TrainerRoad integration

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_routes.py
```

## Deployment

### Raspberry Pi

The application is designed to run on Raspberry Pi. See `docs/DEPLOYMENT.md` for detailed instructions.

Key considerations:
- Use Gunicorn with 2-4 workers
- Enable systemd service for auto-start
- Configure nginx as reverse proxy
- Set up log rotation

### Docker

```bash
# Build image
docker build -t ride-optimizer:3.0.0 .

# Run container
docker run -p 5000:5000 ride-optimizer:3.0.0
```

## Environment Variables

Required environment variables:

```bash
# Flask configuration
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key

# Strava API
STRAVA_CLIENT_ID=your-client-id
STRAVA_CLIENT_SECRET=your-client-secret

# Weather API
OPENWEATHER_API_KEY=your-api-key

# TrainerRoad (optional)
TRAINERROAD_USERNAME=your-username
TRAINERROAD_PASSWORD=your-password
```

## API Endpoints

### Health & Status
- `GET /api/health` - Health check
- `GET /api/status` - Detailed system status
- `GET /api/metrics` - Prometheus metrics

### Data Sync
- `POST /api/sync` - Trigger data synchronization
- `GET /api/jobs` - List background jobs
- `GET /api/jobs/<id>` - Get job status

### Cache Management
- `GET /api/cache/stats` - Cache statistics
- `POST /api/cache/clear` - Clear cache

## Development

### Adding a New Route

1. Create route function in appropriate blueprint
2. Add template in `templates/<blueprint>/`
3. Update navigation in `base.html` if needed
4. Add tests in `tests/test_routes.py`

### Adding a New Blueprint

1. Create new file in `app/routes/`
2. Define blueprint and routes
3. Register in `app/__init__.py`
4. Create template directory
5. Add tests

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>
```

### Template Not Found

Ensure templates are in the correct directory structure:
- `app/templates/base.html`
- `app/templates/<blueprint>/<template>.html`

### Static Files Not Loading

Check that static files are in:
- `app/static/css/`
- `app/static/js/`

## Next Steps

1. **Issue #130**: Extract shared service layer
2. **Issue #131**: Add SQLite persistence
3. **Issue #137**: Implement background jobs
4. **Issue #89**: Complete data persistence layer

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Flask Blueprints](https://flask.palletsprojects.com/en/latest/blueprints/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)