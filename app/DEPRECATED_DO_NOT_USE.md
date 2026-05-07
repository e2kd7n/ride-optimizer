# ⚠️ DEPRECATED - DO NOT USE

This directory contains the DEPRECATED Full Flask implementation with Jinja templates.

**DO NOT MODIFY OR USE THESE FILES**

## Why Deprecated?
The project uses the **Smart Static architecture** (launch.py on port 8083), NOT the Full Flask platform.

## Correct Architecture
- **Static HTML:** `static/dashboard.html`, `static/commute.html`, `static/index.html`
- **Client-side JS:** `static/js/*.js`
- **Minimal API:** `launch.py` with 4 JSON endpoints
- **Services:** `app/services/*.py` (used by API, not templates)

## What to Use Instead
- For web pages: Edit files in `static/` directory
- For APIs: Edit `launch.py`
- For business logic: Edit `app/services/*.py`

## This Directory Contains (DEPRECATED):
- `app/routes_DEPRECATED_FLASK/` - Flask blueprints (NOT USED)
- `app/templates_DEPRECATED_FLASK/` - Jinja2 templates (NOT USED)
- `app/__init__.py` - Flask app factory (NOT USED)

## Active Components (DO USE):
- `app/services/` - Business logic services (ACTIVE - used by launch.py)
- `app/models.py` - Data models (if needed)
- `app/config.py` - Configuration (if needed)

Last updated: 2026-05-07