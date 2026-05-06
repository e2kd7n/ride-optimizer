# Personal Web Platform Proposal: Ride Optimizer v1.0.0

**Date:** 2026-05-06
**Version:** 1.0.0 (Web Platform Launch)
**Project:** Strava Commute Analyzer → Personal Ride Optimizer Web Platform
**Deployment:** Raspberry Pi (Home Network)

> **Note:** This proposal represents version 1.0.0 of the Ride Optimizer project. Previous CLI-based releases (v2.0.0-v2.4.0) have been restated as v0.1.0-v0.5.0 to reflect their prototype nature. See [`VERSIONING_PLAN.md`](VERSIONING_PLAN.md) for details.

---

## Executive Summary

Transform the desktop application into a **personal web platform** running on a Raspberry Pi, providing easy browser-based access to intelligent route analysis and ride planning from any device on your home network.

### Vision
"Optimize your cycling experience with intelligent commute recommendations and personalized long ride planning, accessible from any device at home."

### Core Value Propositions

#### 1. Optimal Commute Intelligence
**Show me the ideal commute to/from work in the next 24 hours**
- Real-time weather analysis with wind impact calculations
- Historical route performance data
- Time-of-day traffic patterns
- Automated daily analysis at 3am for fresh morning recommendations

#### 2. Long Ride Route Planning
**Propose optimal long ride routes based on my preferences**
- Input parameters:
  - Origin point and start time
  - Target distance and/or planned duration
  - Surface type preferences (road, gravel, mixed)
- Route recommendations based on:
  - Historical ride data
  - Weather conditions
  - Elevation profiles
  - Your riding patterns

### Key Features
1. **Web-Based Interface** - Access from laptop or mobile browser
2. **Automated Analysis** - Daily 3am runs for fresh commute data
3. **Interactive Planning** - Form-based long ride route builder
4. **Personal Data Only** - Single-user system, no social features
5. **Privacy-First** - All data stays on your local network

---

## Architecture

### Tech Stack (Lightweight for Raspberry Pi)

**Backend:**
- **Flask** - Lightweight Python web framework (simpler than FastAPI for single-user)
- **SQLite** - Embedded database (no separate DB server needed)
- **Python 3.8+** - Existing codebase compatibility

**Frontend:**
- **Bootstrap 5** - Responsive UI framework (already in use)
- **Vanilla JavaScript** - No heavy frameworks needed
- **Folium/Leaflet** - Interactive maps (already in use)

**Infrastructure:**
- **Raspberry Pi 4** (2GB+ RAM recommended)
- **Podman Container** - Existing deployment method
- **Systemd** - Service management and scheduling
- **Local Network Only** - No external exposure initially

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    Home Network                          │
│                                                          │
│  ┌──────────┐         ┌─────────────────────┐          │
│  │ Laptop/  │────────▶│   Raspberry Pi      │          │
│  │ Mobile   │  HTTP   │                     │          │
│  └──────────┘         │  ┌───────────────┐  │          │
│                       │  │ Flask Web App │  │          │
│                       │  └───────┬───────┘  │          │
│                       │          │          │          │
│                       │  ┌───────▼───────┐  │          │
│                       │  │ Analysis Core │  │          │
│                       │  │ (Existing)    │  │          │
│                       │  └───────┬───────┘  │          │
│                       │          │          │          │
│                       │  ┌───────▼───────┐  │          │
│                       │  │ SQLite DB     │  │          │
│                       │  │ Cache Files   │  │          │
│                       │  └───────────────┘  │          │
│                       │          │          │          │
│                       │  ┌───────▼───────┐  │          │
│                       │  │ Strava API    │──┼─────────▶│
│                       │  └───────────────┘  │  Internet│
│                       └─────────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. User accesses web interface via browser
2. Flask serves pages and handles API requests
3. Analysis core processes Strava data (existing modules)
4. Results cached in SQLite and file system
5. Interactive maps and reports rendered in browser

---

## Core Features

### 1. Web Dashboard (Home Page)

**Quick Stats:**
- Last analysis timestamp
- Total activities analyzed
- Current optimal commute route
- Next scheduled analysis time

**Action Cards:**
- "View Today's Commute Recommendation"
- "Plan a Long Ride"
- "View All Routes"
- "Run Analysis Now"

### 2. Commute Recommendations

**Daily Automated Analysis (3am):**
- Fetches latest Strava activities
- Updates route analysis
- Generates fresh weather forecasts
- Calculates optimal routes for next 24 hours

**Commute View:**
- **Morning Commute** (to work)
  - Recommended route with rationale
  - Weather conditions and wind impact
  - Estimated time and distance
  - Alternative routes
- **Evening Commute** (from work)
  - Same details as morning
  - Updated weather forecast

**Interactive Map:**
- Click routes to see details
- Toggle between alternatives
- View elevation profiles
- See historical performance

### 3. Long Ride Route Planner

**Planning Form:**
```
┌─────────────────────────────────────────┐
│ Plan Your Long Ride                     │
├─────────────────────────────────────────┤
│ Origin Point:                           │
│ ○ Home  ○ Work  ○ Custom Location      │
│ [Map picker for custom]                 │
│                                         │
│ Start Time:                             │
│ [Date/Time picker]                      │
│                                         │
│ Target:                                 │
│ ○ Distance: [40] km                     │
│ ○ Duration: [2.0] hours                 │
│ ○ Both (find routes matching both)      │
│                                         │
│ Surface Type:                           │
│ ☑ Road  ☐ Gravel  ☐ Mixed              │
│                                         │
│ [Generate Recommendations]              │
└─────────────────────────────────────────┘
```

**Recommendations Output:**
- Top 5 route suggestions based on:
  - Historical rides matching criteria
  - Weather conditions at start time
  - Elevation profiles
  - Surface type preferences
- Each route shows:
  - Map preview
  - Distance and estimated duration
  - Elevation gain
  - Surface breakdown
  - Weather forecast
  - Link to similar past rides

### 4. Route Library

**Browse All Routes:**
- Commute routes (to/from work)
- Long ride routes (>15km)
- Filter by:
  - Distance range
  - Date range
  - Route type (loop vs point-to-point)
  - Surface type

**Route Details Page:**
- Interactive map
- Performance statistics
- Weather history
- All activities using this route
- Export to GPX

### 5. Settings & Configuration

**User Preferences:**
- Home/work locations (auto-detected, manual override)
- Preferred units (imperial/metric)
- Commute time windows
- Long ride criteria (min distance)
- Weather preferences

**Analysis Settings:**
- Optimization weights (time/distance/safety/weather)
- Route similarity threshold
- Cache duration
- Scheduled analysis time

**System Status:**
- Last Strava sync
- Cache statistics
- Scheduled job status
- System resources (Pi temperature, memory)

---

## Privacy & Security

### Privacy-First Principles
1. **Local Only** - All data stays on your Raspberry Pi
2. **No External Access** - Home network only (initially)
3. **Single User** - No authentication needed on local network
4. **Data Control** - Easy export and deletion
5. **Strava OAuth** - Secure token storage with encryption

### Security Measures
- Encrypted token storage (existing implementation)
- HTTPS optional (for future remote access)
- Regular security updates via container rebuilds
- No data sharing or telemetry
- Firewall rules for Pi (block external access)

### Future: Remote Access (Optional)
If you want to access from outside home:
- VPN connection (recommended)
- Or: Cloudflare Tunnel / Tailscale
- Or: Port forwarding with HTTPS + authentication

---

## Implementation Plan (Version 1.0.0)

> **Target Release:** v1.0.0 - Q3 2026 (8-10 weeks from approval)
> **Current Version:** v0.5.0 (CLI-based system)
> **See also:** [`VERSIONING_PLAN.md`](VERSIONING_PLAN.md) for complete versioning strategy

### Phase 1: Web Interface Foundation (2-3 weeks)

**Week 1: Flask Setup**
- Create Flask application structure
- Port existing analysis to web endpoints
- Basic routing and templates
- Serve existing HTML reports via web

**Week 2: Dashboard & Commute View**
- Build main dashboard
- Commute recommendation page
- Integrate existing visualizations
- Mobile-responsive design

**Week 3: Testing & Polish**
- Test on Raspberry Pi
- Performance optimization
- Mobile browser testing
- Documentation

**Deliverable:** Working web interface for commute analysis

### Phase 2: Long Ride Planner (2-3 weeks)

**Week 1: Planning Form**
- Build route planning interface
- Location picker (map-based)
- Parameter input forms
- Form validation

**Week 2: Route Generation Logic**
- Algorithm for finding matching routes
- Weather integration for future rides
- Route scoring and ranking
- Results presentation

**Week 3: Integration & Testing**
- Connect to existing route analyzer
- Test various scenarios
- Performance tuning
- User testing

**Deliverable:** Functional long ride planning feature

### Phase 3: Automation & Polish (1-2 weeks)

**Week 1: Scheduled Jobs**
- Systemd timer for 3am analysis
- Background job management
- Error handling and logging
- Email/notification options (optional)

**Week 2: Final Polish**
- Route library browser
- Settings page
- System status dashboard
- Performance optimization
- Documentation

**Deliverable:** Complete personal web platform

### Phase 4: Future Enhancements (Post-1.0)

**Version 1.1.0+ Roadmap:**
- **v1.1.0** - Route library browser, historical trends, advanced settings
- **v1.2.0** - PWA support, offline mode, push notifications
- **v1.3.0** - ML predictions, training plans, performance insights
- **v2.0.0** - Multi-user support, cloud deployment, API access

See [`VERSIONING_PLAN.md`](VERSIONING_PLAN.md) for complete roadmap.

---

## Technical Considerations

### Raspberry Pi Optimization

**Resource Management:**
- **Memory:** Limit Flask workers (1-2 for single user)
- **CPU:** Background analysis during off-hours (3am)
- **Storage:** Regular cache cleanup, log rotation
- **Network:** Local only reduces latency

**Performance Targets:**
- Page load: <2 seconds
- Analysis run: <5 minutes (background)
- Map rendering: <3 seconds
- API response: <500ms

**Monitoring:**
- CPU temperature monitoring
- Memory usage alerts
- Disk space checks
- Service health checks

### Database Schema (SQLite)

**Tables:**
```sql
-- Activities (cached from Strava)
activities (id, strava_id, name, date, distance, duration, ...)

-- Routes (analyzed route groups)
routes (id, name, type, avg_distance, avg_duration, ...)

-- Route Activities (many-to-many)
route_activities (route_id, activity_id)

-- Analysis Results (daily commute recommendations)
analysis_results (id, date, direction, recommended_route_id, ...)

-- Long Ride Plans (saved planning sessions)
long_ride_plans (id, created_at, origin, target_distance, ...)

-- Settings (user preferences)
settings (key, value)
```

### Scheduled Jobs (Systemd)

**Daily Analysis Timer:**
```ini
[Unit]
Description=Ride Optimizer Daily Analysis
Requires=ride-optimizer.service

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Job Tasks:**
1. Fetch new Strava activities
2. Update route analysis
3. Generate commute recommendations
4. Update weather forecasts
5. Clean old cache data
6. Log results

---

## Migration from Current System

### What Stays the Same
- ✅ All existing analysis algorithms
- ✅ Strava OAuth authentication
- ✅ Route similarity detection (Fréchet distance)
- ✅ Weather integration
- ✅ Interactive maps (Folium)
- ✅ Podman container deployment
- ✅ Cache system

### What Changes
- 🔄 CLI → Web interface
- 🔄 Manual execution → Scheduled + on-demand
- 🔄 File-based reports → Database + web pages
- 🔄 Single HTML file → Multi-page web app
- 🔄 Local file access → HTTP server

### Migration Steps
1. Keep existing code as analysis core
2. Add Flask wrapper around existing modules
3. Create web templates using existing HTML reports as base
4. Add SQLite for persistent state
5. Set up systemd services
6. Test thoroughly before switching

---

## Success Metrics

### Functionality
- ✅ Daily automated analysis runs successfully
- ✅ Commute recommendations accurate and timely
- ✅ Long ride planner generates relevant routes
- ✅ Web interface accessible from all home devices
- ✅ Mobile browser experience smooth

### Performance
- ✅ Page loads <2 seconds
- ✅ Analysis completes in <5 minutes
- ✅ Pi temperature stays <70°C under load
- ✅ Memory usage <1GB
- ✅ 99% uptime

### User Experience
- ✅ No command line needed for daily use
- ✅ Intuitive interface (no manual needed)
- ✅ Fast enough for interactive use
- ✅ Reliable scheduled updates
- ✅ Easy to plan rides on the fly

---

## Cost & Resources

### Hardware (Already Owned)
- Raspberry Pi 4 (2GB+ RAM)
- SD card (16GB+)
- Power supply
- Network connection

### Software (Free & Open Source)
- Raspberry Pi OS
- Python 3.8+
- Flask
- SQLite
- Podman
- All existing dependencies

### Time Investment
- **Development:** 6-8 weeks (part-time)
- **Testing:** 1-2 weeks
- **Maintenance:** ~1 hour/month

### Total Cost
- **Hardware:** $0 (already owned)
- **Software:** $0 (all open source)
- **Cloud Hosting:** $0 (local only)
- **Total:** $0

---

## Comparison: Original vs Personal Proposal

| Aspect | Original Proposal | Personal Proposal |
|--------|------------------|-------------------|
| **Users** | Multi-tenant (10,000+) | Single user (you) |
| **Infrastructure** | Kubernetes on AWS/GCP | Raspberry Pi at home |
| **Database** | PostgreSQL + PostGIS | SQLite |
| **Backend** | FastAPI + Celery | Flask (simpler) |
| **Frontend** | Next.js + React | Bootstrap + Vanilla JS |
| **Social Features** | Yes (follow, share, rate) | No (personal use) |
| **Authentication** | OAuth + user management | Strava OAuth only |
| **Monetization** | Subscription tiers | None (hobby project) |
| **Cost** | $325K development | $0 (DIY) |
| **Timeline** | 12 months (team) | 6-8 weeks (solo) |
| **Complexity** | High (scalable system) | Low (single user) |
| **Maintenance** | Ongoing team | Minimal (automated) |

---

## Next Steps

### Immediate Actions (This Week)
1. ✅ Review and approve this proposal
2. Create Flask application skeleton
3. Set up development environment
4. Port first feature (dashboard) to web

### Short Term (Next Month)
1. Complete Phase 1 (web interface)
2. Deploy to Raspberry Pi for testing
3. Gather feedback and iterate
4. Begin Phase 2 (long ride planner)

### Medium Term (2-3 Months)
1. Complete all phases
2. Full testing on Pi
3. Set up scheduled jobs
4. Documentation and user guide
5. Launch for personal use

### Future Considerations
1. Monitor usage and performance
2. Add features as needed
3. Consider cloud deployment if sharing with others
4. Evaluate mobile app (PWA)
5. Explore integration with cycling computers

---

## Appendix: Technical Architecture Details

### Flask Application Structure
```
ride-optimizer-web/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes/
│   │   ├── dashboard.py     # Main dashboard
│   │   ├── commute.py       # Commute recommendations
│   │   ├── planner.py       # Long ride planner
│   │   ├── routes.py        # Route library
│   │   └── settings.py      # Settings & config
│   ├── templates/           # Jinja2 templates
│   ├── static/              # CSS, JS, images
│   ├── models/              # SQLite models
│   └── services/            # Business logic
│       ├── analyzer.py      # Wraps existing analysis
│       ├── scheduler.py     # Background jobs
│       └── strava.py        # Strava API wrapper
├── src/                     # Existing analysis code
├── config/
│   ├── config.yaml          # Existing config
│   └── flask_config.py      # Flask-specific config
├── migrations/              # Database migrations
├── tests/
└── wsgi.py                  # WSGI entry point
```

### API Endpoints
```
GET  /                       # Dashboard
GET  /commute                # Today's commute recommendations
GET  /commute/history        # Past commute data
POST /analysis/run           # Trigger analysis manually
GET  /planner                # Long ride planning form
POST /planner/generate       # Generate route recommendations
GET  /routes                 # Route library
GET  /routes/<id>            # Route details
GET  /settings               # Settings page
POST /settings               # Update settings
GET  /api/status             # System status (JSON)
GET  /api/weather            # Current weather (JSON)
```

### Systemd Service Files
```ini
# /etc/systemd/system/ride-optimizer-web.service
[Unit]
Description=Ride Optimizer Web Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ride-optimizer
ExecStart=/usr/bin/podman-compose up
Restart=always

[Install]
WantedBy=multi-user.target
```

---

**Prepared By:** Senior Development Team (Bob & Assistant)  
**Date:** 2026-05-06  
**Status:** Ready for Review and Implementation
---

## Version 1.0.0 Success Criteria

### Must-Have Features (Blocking Release)
- ✅ Web dashboard accessible from laptop and mobile
- ✅ Automated daily analysis at 3am
- ✅ Commute recommendations view
- ✅ Long ride route planner with form interface
- ✅ SQLite database for persistence
- ✅ Mobile-responsive design
- ✅ Raspberry Pi deployment
- ✅ Systemd service management

### Performance Targets
- Page loads: <2 seconds
- Analysis runtime: <5 minutes
- API response: <500ms
- Uptime: 99% over 30 days

### Quality Gates
- All existing tests passing
- New web interface tests added
- Security audit completed
- Documentation updated
- User testing completed

**Related Documents:**
- [`VERSIONING_PLAN.md`](VERSIONING_PLAN.md) - Version strategy and roadmap
- [`WEB_PLATFORM_PROPOSAL.md`](archive/WEB_PLATFORM_PROPOSAL.md) - Original multi-user proposal (archived)
