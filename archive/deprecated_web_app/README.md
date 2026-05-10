# Deprecated Web App Files

**Date Archived:** 2026-05-10  
**Reason:** Epic #237 UI/UX Redesign - Phase 3 HTML Restructuring

## What Was Archived

These files were part of the original 4-tab navigation system:
- `dashboard.html` - Original home/dashboard page
- `commute.html` - Commute recommendations page
- `planner.html` - Ride planner page (placeholder)

## Why They Were Archived

Issue #257 Phase 3 restructured the web app to use a 3-tab navigation system:
1. **Home** (replaces Dashboard + Commute functionality)
2. **Routes** (route library)
3. **Settings** (user preferences)

The new structure consolidates functionality and aligns with Epic #237's design vision.

## New File Structure

| Old File | New Location | Notes |
|----------|--------------|-------|
| `dashboard.html` | `static/index.html` (Home tab) | Dashboard + weather + commute in one view |
| `commute.html` | `static/index.html` (Home tab) | Commute recommendations integrated into Home |
| `planner.html` | `static/index.html` (Home tab) | Planner functionality to be added to Home |
| `routes.html` | `static/routes.html` | Updated with 3-tab navigation |
| N/A | `static/settings.html` | New standalone settings page |

## Navigation Changes

**Old (4-tab):**
- Dashboard
- Commute  
- Planner
- Routes

**New (3-tab):**
- Home (combines Dashboard + Commute + Planner)
- Routes
- Settings

## Do Not Use These Files

These files are kept for reference only. They use the deprecated 4-tab navigation and are NOT served by `launch.py`.

For current implementation, see:
- `static/index.html`
- `static/routes.html`
- `static/settings.html`