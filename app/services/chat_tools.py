"""
Read-only data tools for the Reports-page ride chat (#608).

Each tool is a thin wrapper over data the app already computes (the shared
activity cache, the gear cache, the route library) and returns compact JSON
for Claude to reason over — the dataset itself is never put in the prompt.

Privacy: tool output carries aggregates and activity metadata only (dates,
distance, time, elevation, gear, names). Activity rows are built from an
explicit field list, so start/end coordinates and polylines can't leak in
by accident, and every result is passed through src/pii_sanitizer.py on the
way out.
"""

import json
from collections import OrderedDict
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

# The Reports page's own aggregation helpers, so chat answers match the
# numbers on the page (same local-date bucketing, same unit conversions).
from app.api.stats_bp import (
    _activity_local_start,
    _compute_records,
    _compute_summary,
    _meters_to_feet,
    _meters_to_miles,
    _ms_to_mph,
    _seconds_to_hours,
)
from src.pii_sanitizer import (
    sanitize_address,
    sanitize_coordinates,
    sanitize_email,
    sanitize_token,
)

_WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
_MAX_ROWS = 50
_MAX_BUCKETS = 120

_SORT_KEYS = {
    'date_desc': (lambda a: a['_start'], True),
    'date_asc': (lambda a: a['_start'], False),
    'distance_desc': (lambda a: a['_act'].distance or 0, True),
    'elevation_desc': (lambda a: a['_act'].total_elevation_gain or 0, True),
    'speed_desc': (lambda a: a['_act'].average_speed or 0, True),
    'time_desc': (lambda a: a['_act'].moving_time or 0, True),
}

_FILTER_PROPERTIES = {
    'start_date': {'type': 'string', 'description': 'Inclusive start date, YYYY-MM-DD (ride-local calendar date).'},
    'end_date': {'type': 'string', 'description': 'Inclusive end date, YYYY-MM-DD (ride-local calendar date).'},
    'sport_type': {
        'type': 'string',
        'description': "Exact Strava sport type, e.g. 'Ride', 'GravelRide', 'EBikeRide', 'VirtualRide', 'Run'.",
    },
    'gear_id': {'type': 'string', 'description': 'Only activities recorded with this gear id (see list_gear).'},
    'weekdays': {
        'type': 'array',
        'items': {'type': 'string', 'enum': _WEEKDAYS},
        'description': 'Only activities that started on these days of the week.',
    },
    'min_distance_mi': {'type': 'number', 'description': 'Minimum distance in miles.'},
    'max_distance_mi': {'type': 'number', 'description': 'Maximum distance in miles.'},
    'name_contains': {'type': 'string', 'description': 'Case-insensitive substring of the activity name.'},
}

# Order is fixed: the tool list is part of the cached prompt prefix.
TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        'name': 'get_totals',
        'description': (
            "Aggregate totals (ride count, distance, moving time, elevation, averages, kudos, kilojoules) "
            "over the rider's cached activities, optionally filtered and grouped. Use group_by='none' for a "
            "single summary, which also includes personal records and the first/last date matched. Group by "
            "week, month or year for trends and period comparisons; by weekday, sport_type or gear for "
            "breakdowns. Distances are miles, elevation feet, time hours, speed mph."
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'group_by': {
                    'type': 'string',
                    'enum': ['none', 'week', 'month', 'year', 'weekday', 'sport_type', 'gear'],
                    'description': "How to bucket the matching activities. Defaults to 'none'.",
                },
                **_FILTER_PROPERTIES,
            },
            'additionalProperties': False,
        },
    },
    {
        'name': 'search_activities',
        'description': (
            "Find individual activities matching filters and return compact rows (date, weekday, local start "
            "time, name, sport type, distance, time, elevation, speed, heart rate, power, gear id), plus a "
            f"summary of every match. Returns at most {_MAX_ROWS} rows; use sort_by and limit to get e.g. the "
            "longest weekday ride or the most recent gravel rides."
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                **_FILTER_PROPERTIES,
                'sort_by': {
                    'type': 'string',
                    'enum': list(_SORT_KEYS),
                    'description': "Row order. Defaults to 'date_desc'.",
                },
                'limit': {'type': 'integer', 'description': f'Rows to return, 1-{_MAX_ROWS}. Defaults to 20.'},
            },
            'additionalProperties': False,
        },
    },
    {
        'name': 'list_gear',
        'description': (
            "List the rider's bikes and shoes with lifetime totals computed from cached activities, the date "
            "each was last used, and Strava's own odometer reading. For mileage since a date (e.g. since a "
            "chain swap), call get_totals with group_by='gear' and start_date instead."
        ),
        'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
    },
    {
        'name': 'list_routes',
        'description': (
            "List routes from the rider's route library: commute routes (grouped by direction) and long "
            "rides, with name, distance, typical duration, elevation, how many times ridden and when last "
            "ridden."
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'route_type': {
                    'type': 'string',
                    'enum': ['all', 'commute', 'long_ride'],
                    'description': "Defaults to 'all'.",
                },
                'sort_by': {
                    'type': 'string',
                    'enum': ['uses', 'distance', 'recent', 'name'],
                    'description': "Defaults to 'uses'.",
                },
                'limit': {'type': 'integer', 'description': f'Routes to return, 1-{_MAX_ROWS}. Defaults to 20.'},
            },
            'additionalProperties': False,
        },
    },
]


class ToolInputError(ValueError):
    """A tool was called with arguments it can't use; reported back to Claude as an error result."""


def sanitize_outbound(text: str) -> str:
    """Final PII pass over anything about to leave the app for the Claude API."""
    for fn in (sanitize_coordinates, sanitize_address, sanitize_email, sanitize_token):
        text = fn(text)
    return text


def _parse_date(value: Optional[str], field: str) -> Optional[date]:
    if value in (None, ''):
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        raise ToolInputError(f"{field} must be YYYY-MM-DD, got {value!r}")


def _clamp_limit(value: Any, default: int = 20) -> int:
    try:
        n = int(value) if value is not None else default
    except (TypeError, ValueError):
        raise ToolInputError(f"limit must be an integer, got {value!r}")
    return max(1, min(n, _MAX_ROWS))


def _activity_row(a, start: datetime) -> Dict[str, Any]:
    """Compact, explicit-field view of one activity. Never add location fields here."""
    return {
        'date': start.strftime('%Y-%m-%d'),
        'weekday': _WEEKDAYS[start.weekday()],
        'start_time': start.strftime('%H:%M'),
        'name': a.name,
        'sport_type': a.sport_type or a.type,
        'distance_mi': round(_meters_to_miles(a.distance or 0), 1),
        'moving_time_h': round(_seconds_to_hours(a.moving_time or 0), 2),
        'elevation_ft': round(_meters_to_feet(a.total_elevation_gain or 0)),
        'avg_speed_mph': round(_ms_to_mph(a.average_speed or 0), 1),
        'avg_heartrate': round(a.average_heartrate) if a.average_heartrate else None,
        'avg_watts': round(a.average_watts) if a.average_watts else None,
        'kilojoules': round(a.kilojoules) if a.kilojoules else None,
        'gear_id': a.gear_id,
    }


class ChatTools:
    """Executes the chat's tool calls against the app's existing data sources.

    Sources are callables so the tools always read whatever the container
    currently holds (a refreshed AnalysisService, a rewritten cache file).
    """

    def __init__(self,
                 activities_source: Callable[[], List[Any]],
                 gear_source: Callable[[], Optional[Dict[str, Any]]],
                 route_library_source: Callable[[], Any]):
        self._activities_source = activities_source
        self._gear_source = gear_source
        self._route_library_source = route_library_source
        self._handlers = {
            'get_totals': self._get_totals,
            'search_activities': self._search_activities,
            'list_gear': self._list_gear,
            'list_routes': self._list_routes,
        }

    @property
    def definitions(self) -> List[Dict[str, Any]]:
        return TOOL_DEFINITIONS

    def execute(self, name: str, args: Optional[Dict[str, Any]]) -> str:
        """Run one tool and return its sanitized JSON result.

        Raises ToolInputError for an unknown tool or bad arguments.
        """
        handler = self._handlers.get(name)
        if handler is None:
            raise ToolInputError(f"Unknown tool {name!r}")
        result = handler(dict(args or {}))
        return sanitize_outbound(json.dumps(result, separators=(',', ':'), default=str))

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _matching(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Activities passing the shared filters, each paired with its local start."""
        start_date = _parse_date(args.get('start_date'), 'start_date')
        end_date = _parse_date(args.get('end_date'), 'end_date')
        sport_type = args.get('sport_type') or None
        gear_id = args.get('gear_id') or None
        weekdays = args.get('weekdays') or None
        if weekdays is not None:
            bad = [d for d in weekdays if d not in _WEEKDAYS]
            if bad:
                raise ToolInputError(f"weekdays must be full day names, got {bad!r}")
            weekday_idx = {_WEEKDAYS.index(d) for d in weekdays}
        name_contains = (args.get('name_contains') or '').lower() or None
        min_m = args.get('min_distance_mi')
        max_m = args.get('max_distance_mi')
        try:
            min_m = float(min_m) / 0.000621371 if min_m is not None else None
            max_m = float(max_m) / 0.000621371 if max_m is not None else None
        except (TypeError, ValueError):
            raise ToolInputError("min_distance_mi / max_distance_mi must be numbers")

        out = []
        for a in self._activities_source():
            if not a.start_date and not getattr(a, 'start_date_local', None):
                continue
            try:
                start = _activity_local_start(a)
            except (ValueError, AttributeError):
                continue
            d = start.date()
            if start_date and d < start_date:
                continue
            if end_date and d > end_date:
                continue
            if sport_type and (a.sport_type or a.type) != sport_type:
                continue
            if gear_id and a.gear_id != gear_id:
                continue
            if weekdays is not None and start.weekday() not in weekday_idx:
                continue
            if min_m is not None and (a.distance or 0) < min_m:
                continue
            if max_m is not None and (a.distance or 0) > max_m:
                continue
            if name_contains and name_contains not in (a.name or '').lower():
                continue
            out.append({'_act': a, '_start': start})
        return out

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _get_totals(self, args: Dict[str, Any]) -> Dict[str, Any]:
        group_by = args.get('group_by') or 'none'
        matches = self._matching(args)
        acts = [m['_act'] for m in matches]

        if group_by == 'none':
            starts = sorted(m['_start'] for m in matches)
            records = _compute_records(acts)
            for r in records.values():
                r.pop('id', None)
            return {
                'summary': _compute_summary(acts),
                'records': records,
                'first_date': starts[0].strftime('%Y-%m-%d') if starts else None,
                'last_date': starts[-1].strftime('%Y-%m-%d') if starts else None,
            }

        if group_by in ('week', 'month', 'year'):
            fmt = {'week': '%G-W%V', 'month': '%Y-%m', 'year': '%Y'}[group_by]
            key_fn = lambda m: m['_start'].strftime(fmt)  # noqa: E731
        elif group_by == 'weekday':
            key_fn = lambda m: _WEEKDAYS[m['_start'].weekday()]  # noqa: E731
        elif group_by == 'sport_type':
            key_fn = lambda m: m['_act'].sport_type or m['_act'].type or 'Unknown'  # noqa: E731
        elif group_by == 'gear':
            names = self._gear_names()
            key_fn = lambda m: m['_act'].gear_id or 'unassigned'  # noqa: E731
        else:
            raise ToolInputError(f"Unknown group_by {group_by!r}")

        buckets: 'OrderedDict[str, list]' = OrderedDict()
        for m in sorted(matches, key=lambda m: m['_start']):
            buckets.setdefault(key_fn(m), []).append(m['_act'])

        keys = list(buckets)
        if group_by == 'weekday':
            keys.sort(key=_WEEKDAYS.index)
        truncated = len(keys) > _MAX_BUCKETS
        if truncated:
            keys = keys[-_MAX_BUCKETS:]  # most recent periods

        groups = []
        for k in keys:
            entry = {'group': k, **_compute_summary(buckets[k])}
            if group_by == 'gear':
                entry['gear_name'] = names.get(k, 'No gear recorded' if k == 'unassigned' else k)
            groups.append(entry)
        result = {'group_by': group_by, 'groups': groups}
        if truncated:
            result['note'] = f'Only the most recent {_MAX_BUCKETS} groups are shown; narrow the date range for older ones.'
        return result

    def _search_activities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sort_by = args.get('sort_by') or 'date_desc'
        if sort_by not in _SORT_KEYS:
            raise ToolInputError(f"Unknown sort_by {sort_by!r}")
        limit = _clamp_limit(args.get('limit'))
        matches = self._matching(args)
        key, reverse = _SORT_KEYS[sort_by]
        matches.sort(key=key, reverse=reverse)
        return {
            'total_matches': len(matches),
            'returned': min(limit, len(matches)),
            'summary_of_matches': _compute_summary([m['_act'] for m in matches]),
            'activities': [_activity_row(m['_act'], m['_start']) for m in matches[:limit]],
        }

    def _gear_names(self) -> Dict[str, str]:
        gear = self._gear_source() or {}
        return {g['id']: g.get('name') or g['id'] for g in gear.get('bikes', []) + gear.get('shoes', [])}

    def _list_gear(self, args: Dict[str, Any]) -> Dict[str, Any]:
        gear_cache = self._gear_source()
        buckets: Dict[str, list] = {}
        for a in self._activities_source():
            if a.gear_id:
                buckets.setdefault(a.gear_id, []).append(a)

        items = []
        known = set()
        for g in (gear_cache or {}).get('bikes', []) + (gear_cache or {}).get('shoes', []):
            known.add(g['id'])
            acts = buckets.get(g['id'], [])
            items.append(self._gear_entry(g['id'], g, acts))
        for gid, acts in buckets.items():
            if gid not in known:
                items.append(self._gear_entry(gid, {'name': gid, 'type': 'unknown'}, acts))
        items.sort(key=lambda g: (0 if g['type'] == 'bike' else 1, -g['total_distance_mi']))
        return {'gear': items, 'gear_cache_available': gear_cache is not None}

    @staticmethod
    def _gear_entry(gear_id: str, meta: Dict[str, Any], acts: List[Any]) -> Dict[str, Any]:
        last = None
        for a in acts:
            try:
                s = _activity_local_start(a)
            except (ValueError, AttributeError):
                continue
            if last is None or s > last:
                last = s
        entry = {
            'gear_id': gear_id,
            'name': meta.get('name') or gear_id,
            'type': meta.get('type', 'unknown'),
            'brand': meta.get('brand_name') or None,
            'model': meta.get('model_name') or None,
            'primary': bool(meta.get('primary', False)),
            'last_used': last.strftime('%Y-%m-%d') if last else None,
            **_compute_summary(acts),
        }
        if meta.get('strava_distance_m'):
            entry['strava_odometer_mi'] = round(_meters_to_miles(meta['strava_distance_m']), 1)
        return entry

    def _list_routes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        route_type = args.get('route_type') or 'all'
        sort_by = args.get('sort_by') or 'uses'
        if route_type not in ('all', 'commute', 'long_ride'):
            raise ToolInputError(f"Unknown route_type {route_type!r}")
        if sort_by not in ('uses', 'distance', 'recent', 'name'):
            raise ToolInputError(f"Unknown sort_by {sort_by!r}")
        limit = _clamp_limit(args.get('limit'))

        library = self._route_library_source()
        if library is None:
            return {'routes': [], 'note': 'The route library is unavailable right now.'}
        # No limit here: get_all_routes counts after limiting, and we want the real total.
        result = library.get_all_routes(route_type=route_type, sort_by=sort_by)
        if result.get('status') != 'success':
            return {'routes': [], 'note': result.get('message') or 'No routes found yet; run an analysis first.'}

        all_routes = result.get('routes', [])
        routes = []
        for r in all_routes[:limit]:
            km = r.get('distance') or 0
            routes.append({
                'name': r.get('name'),
                'type': r.get('type'),
                'direction': r.get('direction'),
                'distance_mi': round(km * 0.621371, 1),
                'typical_duration_min': round(r['duration']) if r.get('duration') else None,
                'elevation_ft': round(_meters_to_feet(r.get('elevation') or 0)),
                'times_ridden': r.get('uses'),
                'last_ridden': str(r.get('last_ridden') or '')[:10] or None,
                'is_favorite': bool(r.get('is_favorite')),
            })
        return {'total_routes': len(all_routes), 'routes': routes}
