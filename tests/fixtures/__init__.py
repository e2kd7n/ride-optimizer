"""
Test fixture loading utilities.

Usage:
    from tests.fixtures import load_activities, load_route_groups, load_weather, load_workouts
    from tests.fixtures import make_activity, make_route_group, make_route
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

FIXTURES_DIR = Path(__file__).parent


def _load_json(filename: str) -> Any:
    with open(FIXTURES_DIR / filename) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Raw JSON loaders
# ---------------------------------------------------------------------------

def load_activities() -> List[Dict[str, Any]]:
    """Load all sample activities (22 rides covering commutes, long rides, edge cases)."""
    return _load_json("activities.json")


def load_route_groups() -> Dict[str, Any]:
    """Load route groups fixture (3 groups: home→work, work→home, plus route)."""
    return _load_json("route_groups.json")


def load_weather() -> Dict[str, Any]:
    """Load weather fixture including current conditions, daily and hourly forecast."""
    return _load_json("weather.json")


def load_workouts() -> Dict[str, Any]:
    """Load TrainerRoad workout calendar fixture."""
    return _load_json("workouts.json")


def load_recommendations() -> Dict[str, Any]:
    """Load sample recommendations fixture."""
    return _load_json("sample_recommendations.json")


# ---------------------------------------------------------------------------
# Typed object helpers (instantiate real dataclasses when needed)
# ---------------------------------------------------------------------------

def make_activity(overrides: Optional[Dict[str, Any]] = None):
    """Return an Activity dataclass built from the first fixture entry + optional overrides."""
    from src.data_fetcher import Activity

    data = load_activities()[0].copy()
    if overrides:
        data.update(overrides)
    return Activity.from_dict(data)


def make_activities(n: Optional[int] = None, overrides: Optional[Dict[str, Any]] = None):
    """Return a list of Activity dataclass objects from fixture data.

    Args:
        n: Number of activities to return (None = all).
        overrides: Dict of field overrides applied to every activity.
    """
    from src.data_fetcher import Activity

    raw = load_activities()[:n] if n else load_activities()
    activities = []
    for entry in raw:
        d = entry.copy()
        if overrides:
            d.update(overrides)
        try:
            activities.append(Activity.from_dict(d))
        except Exception:
            pass
    return activities


def make_route(data: Dict[str, Any]):
    """Convert a route dict (from fixture) to a Route dataclass."""
    from src.route_analyzer import Route

    return Route(
        activity_id=data["activity_id"],
        direction=data["direction"],
        coordinates=[tuple(c) for c in data.get("coordinates", [])],
        distance=data["distance"],
        duration=data["duration"],
        elevation_gain=data["elevation_gain"],
        timestamp=data["timestamp"],
        average_speed=data["average_speed"],
        activity_name=data.get("activity_name", ""),
        is_plus_route=data.get("is_plus_route", False),
    )


def make_route_group(data: Dict[str, Any]):
    """Convert a route_group dict (from fixture) to a RouteGroup dataclass."""
    from src.route_analyzer import RouteGroup

    routes = [make_route(r) for r in data.get("routes", [])]
    rep = make_route(data["representative_route"])
    return RouteGroup(
        id=data["id"],
        direction=data["direction"],
        routes=routes,
        representative_route=rep,
        frequency=data["frequency"],
        name=data.get("name"),
        is_plus_route=data.get("is_plus_route", False),
        difficulty=data.get("difficulty", "Easy"),
    )


def make_route_groups():
    """Return all RouteGroup dataclass objects from the fixture."""
    raw = load_route_groups()
    return [make_route_group(g) for g in raw["route_groups"]]
