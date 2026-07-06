"""Commute API Blueprint.

Routes:
  GET /api/recommendation
  GET /api/commute
  GET /api/commute/map
  GET /api/workout-options
"""

from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, current_app, jsonify, request

from src.secure_logger import SecureLogger
from src.weather_fetcher import WindImpactCalculator
from app.schemas import RecommendationQuerySchema, validate_request_args

logger = SecureLogger(__name__)

bp = Blueprint('commute', __name__, url_prefix='/api')


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _enrich_commute_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Add reasons, weather_summary, and time_impact to a recommendation dict."""
    if not rec or rec.get('status') != 'success':
        return rec

    enriched = dict(rec)
    weather = rec.get('weather') or {}
    breakdown = rec.get('breakdown') or {}
    route = rec.get('route') or {}

    # weather_summary — natural language sentence
    temp = weather.get('temperature', 0)
    wind_speed = weather.get('wind_speed', 0)
    wind_dir = weather.get('wind_direction', '')
    conditions = (weather.get('conditions') or '').lower()

    sky_part = 'Clear skies'
    if 'thunder' in conditions or 'storm' in conditions:
        sky_part = 'Stormy'
    elif 'rain' in conditions or 'drizzle' in conditions:
        sky_part = 'Rainy'
    elif 'snow' in conditions:
        sky_part = 'Snowy'
    elif 'cloud' in conditions or 'overcast' in conditions:
        sky_part = 'Cloudy'
    elif 'fog' in conditions or 'mist' in conditions:
        sky_part = 'Foggy'
    elif conditions:
        sky_part = conditions.capitalize()

    wind_part = ''
    if wind_speed >= 15:
        wind_part = f'strong {wind_dir} wind ({round(wind_speed)} mph)'
    elif wind_speed >= 8:
        wind_part = f'light {wind_dir} wind'
    elif wind_speed >= 3:
        wind_part = 'gentle breeze'

    enriched['weather_summary'] = f"{sky_part}{', ' + wind_part if wind_part else ''}"

    # wind_impact — headwind/tailwind analysis for this route
    wind_impact = None
    coords = route.get('coordinates') or []
    wind_deg = weather.get('wind_direction_deg')
    wind_kph = weather.get('wind_speed_kph')
    if len(coords) >= 2 and wind_deg is not None and wind_kph is not None:
        try:
            start = tuple(coords[0])[:2]
            end = tuple(coords[-1])[:2]
            bearing = WindImpactCalculator.calculate_bearing(start, end)
            components = WindImpactCalculator.calculate_wind_component(
                float(wind_kph), float(wind_deg), bearing
            )
            hw_mph = round(components['headwind_kph'] * 0.621371)
            abs_mph = abs(hw_mph)
            if hw_mph > 3:
                label = f'Headwind ~{abs_mph} mph'
                icon = 'bi-wind text-warning'
            elif hw_mph < -3:
                label = f'Tailwind ~{abs_mph} mph'
                icon = 'bi-wind text-success'
            else:
                label = 'Crosswind'
                icon = 'bi-wind text-info'
            wind_impact = {'label': label, 'mph': abs_mph, 'icon': icon,
                           'is_tailwind': hw_mph < -3, 'is_headwind': hw_mph > 3}
        except Exception:
            pass
    enriched['wind_impact'] = wind_impact

    # reasons — 2–4 decision bullets
    reasons = []
    weather_score = breakdown.get('weather', 0)
    if isinstance(weather_score, (int, float)) and weather_score > 0.75:
        reasons.append('Favorable weather for cycling today')
    elif wind_impact and wind_impact.get('is_tailwind') and wind_speed >= 8:
        reasons.append(f"Tailwind advantage — ~{wind_impact['mph']} mph boost")
    elif wind_impact and wind_impact.get('is_headwind') and wind_speed >= 15:
        reasons.append(f"Strong headwind (~{wind_impact['mph']} mph) — expect slower pace")
    elif wind_speed >= 15:
        reasons.append('Strong wind — check if it works as a tailwind')

    frequency = route.get('frequency', 0)
    if frequency >= 10:
        reasons.append('Your most-ridden route — reliable timing')
    elif frequency >= 3:
        reasons.append('A familiar route for you')

    time_score = breakdown.get('time', 0)
    if isinstance(time_score, (int, float)) and time_score > 0.8:
        reasons.append('Optimal timing for your usual commute window')

    safety_score = breakdown.get('safety', 0)
    if isinstance(safety_score, (int, float)) and safety_score > 0.75:
        reasons.append('No known obstacles or hazards')

    if not reasons:
        score = rec.get('score', 0)
        score_val = int(score * 100) if isinstance(score, float) and score <= 1 else int(score)
        if score_val >= 70:
            reasons.append('Best available option given current conditions')
        else:
            reasons.append('Consider checking alternative routes today')

    enriched['reasons'] = reasons[:4]

    # time_impact
    duration_secs = route.get('duration', 0)
    duration_mins = round(duration_secs / 60) if duration_secs else None
    enriched['time_impact'] = {
        'estimated_minutes': duration_mins,
        'vs_average_minutes': None,
        'label': f'~{duration_mins} minutes estimated' if duration_mins else None
    }

    # transit_recommendation
    enriched['transit_recommendation'] = _get_transit_recommendation(weather)
    return enriched


def _get_transit_recommendation(weather: Dict[str, Any]) -> Dict[str, Any]:
    """Return a transit suggestion when cycling conditions are too poor."""
    if not weather:
        return {'suggested': False}

    conditions = (weather.get('conditions') or '').lower()
    comfort_score = weather.get('comfort_score')
    favorability = (weather.get('cycling_favorability') or '').lower()

    is_severe = 'thunder' in conditions or 'storm' in conditions
    is_heavy_precip = 'heavy rain' in conditions or 'heavy snow' in conditions or 'blizzard' in conditions

    if is_severe or is_heavy_precip:
        reason = ('Dangerous conditions — thunderstorm or severe weather' if is_severe
                  else 'Heavy precipitation — cycling not advised')
        return {
            'suggested': True,
            'severity': 'severe',
            'reason': reason,
            'transit_url': 'https://www.google.com/maps?travelmode=transit',
        }

    if favorability == 'unfavorable' or (isinstance(comfort_score, (int, float)) and comfort_score < 0.4):
        temp = weather.get('temperature', weather.get('temp_f'))
        wind_speed = weather.get('wind_speed', weather.get('wind_speed_kph', 0))
        precip_mm = weather.get('precipitation_mm', weather.get('precipitation', 0))

        if 'rain' in conditions or 'drizzle' in conditions or (isinstance(precip_mm, (int, float)) and precip_mm > 2):
            reason = 'Rainy conditions — consider public transit or waiting for a dry window'
        elif 'snow' in conditions:
            reason = 'Snowy conditions — transit may be safer'
        elif isinstance(temp, (int, float)) and temp <= 25:
            reason = f'Very cold ({round(temp)}°F) — transit recommended'
        elif isinstance(temp, (int, float)) and temp >= 95:
            reason = f'Extreme heat ({round(temp)}°F) — consider transit'
        elif isinstance(wind_speed, (int, float)) and wind_speed >= 25:
            reason = f'Very strong winds ({round(wind_speed)} mph) — transit recommended'
        else:
            reason = 'Poor cycling conditions today — transit is a good alternative'

        return {
            'suggested': True,
            'severity': 'poor',
            'reason': reason,
            'transit_url': 'https://www.google.com/maps?travelmode=transit',
        }

    return {'suggested': False}


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@bp.route('/recommendation')
@validate_request_args(RecommendationQuerySchema)
def get_recommendation():
    """Get next commute recommendation."""
    container = current_app.container
    container.initialise()

    commute_service = container.commute_service
    if commute_service is None:
        return jsonify({'status': 'error', 'message': 'Commute is currently unavailable'}), 503

    try:
        direction = request.args.get('direction')
        recommendation = commute_service.get_next_commute(direction)

        if recommendation.get('status') == 'success' and recommendation.get('route'):
            route = recommendation['route']
            score = recommendation.get('score', 0)
            score_percent = int(score * 100) if isinstance(score, float) and score <= 1 else int(score)
            formatted = {
                'status': 'success',
                'direction': recommendation.get('direction'),
                'time_window': recommendation.get('time_window'),
                'is_today': recommendation.get('is_today'),
                'departure_time': recommendation.get('departure_time'),
                'confidence': recommendation.get('confidence'),
                'route': route,
                'recommended_route': {
                    'id': route.get('id'),
                    'name': route.get('name', 'Unknown Route'),
                    'distance': route.get('distance', 0),
                    'duration': route.get('duration', 0),
                    'elevation_gain': route.get('elevation', 0),
                    'coordinates': route.get('coordinates', [])
                },
                'score': score_percent,
                'recommendation': 'Recommended' if score_percent >= 70 else 'Alternative available',
                'breakdown': recommendation.get('breakdown', {}),
                'weather': recommendation.get('weather'),
                'factors': []
            }
            for key, value in formatted['breakdown'].items():
                if isinstance(value, (int, float)):
                    factor_value = int(value * 100) if value <= 1 else int(value)
                    formatted['factors'].append(f"{key.title()}: {factor_value}%")
                elif not isinstance(value, dict):
                    formatted['factors'].append(f"{key.title()}: {value}")

            formatted['timestamp'] = datetime.now().isoformat()
            return jsonify(formatted)
        else:
            recommendation['timestamp'] = datetime.now().isoformat()
            return jsonify(recommendation)

    except Exception as e:
        logger.error(f"Error getting recommendation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Recommendation temporarily unavailable'}), 500


@bp.route('/commute')
def get_commute():
    """Get both commute directions (to_work and to_home) for the commute view."""
    container = current_app.container
    container.initialise()

    commute_service = container.commute_service
    if commute_service is None:
        return jsonify({'status': 'error', 'message': 'Commute is currently unavailable'}), 503

    try:
        trainerroad_service = container.trainerroad_service
        use_workout = (trainerroad_service and trainerroad_service.get_feed_url() is not None)

        if use_workout:
            to_work = _enrich_commute_recommendation(
                commute_service.get_workout_aware_commute(direction='to_work')
            )
            to_home = _enrich_commute_recommendation(
                commute_service.get_workout_aware_commute(direction='to_home')
            )
        else:
            to_work = _enrich_commute_recommendation(
                commute_service.get_next_commute(direction='to_work')
            )
            to_home = _enrich_commute_recommendation(
                commute_service.get_next_commute(direction='to_home')
            )

        workout_ride = None
        planner_service = container.planner_service
        if use_workout and planner_service and planner_service._long_rides:
            from datetime import date as _date
            constraints = trainerroad_service.get_workout_constraints(_date.today())
            if constraints:
                commute_service._apply_weather_indoor_decision(constraints)
                if not constraints.get('indoor_fallback'):
                    home_loc = None
                    try:
                        home_loc = (commute_service._recommender.home_location.lat,
                                    commute_service._recommender.home_location.lon)
                    except Exception:
                        pass
                    rides = planner_service.get_workout_rides(
                        workout_type=constraints.get('workout_type', ''),
                        target_duration_min=constraints.get('min_duration_minutes'),
                        location=home_loc,
                        limit=3,
                    )
                    if rides:
                        workout_ride = {
                            'workout_name': constraints.get('workout_name'),
                            'workout_type': constraints.get('workout_type'),
                            'rides': rides,
                        }

        return jsonify({
            'status': 'success',
            'to_work': to_work,
            'to_home': to_home,
            'workout_ride': workout_ride,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting commute data: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Commute data temporarily unavailable'}), 500


@bp.route('/workout-options')
def get_workout_options():
    """Unified workout options for today's dashboard."""
    container = current_app.container
    container.initialise()

    from datetime import date as _date

    trainerroad_service = container.trainerroad_service
    has_tr = (trainerroad_service and trainerroad_service.get_feed_url() is not None)
    if not has_tr:
        return jsonify({'status': 'no_workout'})

    try:
        constraints = trainerroad_service.get_workout_constraints(_date.today())
        if not constraints or not constraints.get('has_workout'):
            return jsonify({'status': 'no_workout'})

        commute_service = container.commute_service
        if commute_service:
            commute_service._apply_weather_indoor_decision(constraints)

        weather_suitable = not constraints.get('indoor_fallback', False)
        indoor_reason = constraints.get('indoor_reason')

        workout_info = {
            'name': constraints.get('workout_name', 'Workout'),
            'type': constraints.get('workout_type', ''),
            'duration_minutes': constraints.get('min_duration_minutes'),
            'tss': constraints.get('tss'),
        }

        options = {}

        if commute_service:
            try:
                commute_rec = commute_service.get_workout_aware_commute()
                if commute_rec.get('status') == 'success':
                    route = commute_rec.get('route', {})
                    wf = commute_rec.get('workout_fit', {})
                    options['commute'] = {
                        'route': {
                            'id': route.get('id'),
                            'name': route.get('name', 'Commute'),
                            'distance': route.get('distance', 0),
                            'elevation': route.get('elevation', 0),
                        },
                        'fit_score': wf.get('fit_score', 0) if wf else 0,
                        'is_extended': commute_rec.get('is_workout_extended', False),
                        'duration_minutes': round(route.get('duration', 0)) if route.get('duration') else None,
                    }
            except Exception as e:
                logger.warning(f"Workout-options: commute unavailable: {e}")

        planner_service = container.planner_service
        if weather_suitable and planner_service and planner_service._long_rides:
            try:
                home_loc = None
                if commute_service and commute_service._recommender:
                    hl = commute_service._recommender.home_location
                    home_loc = (hl.lat, hl.lon)
                rides = planner_service.get_workout_rides(
                    workout_type=constraints.get('workout_type', ''),
                    target_duration_min=constraints.get('min_duration_minutes'),
                    location=home_loc,
                    limit=3,
                )
                if rides:
                    best = rides[0]
                    options['workout_ride'] = {
                        'route': {
                            'name': best['name'],
                            'distance': best['distance_miles'] * 1.60934,
                            'elevation': best['elevation_ft'] / 3.28084,
                        },
                        'fit_score': best['score'],
                        'duration_minutes': best['duration_minutes'],
                        'alternatives': rides[1:],
                    }
            except Exception as e:
                logger.warning(f"Workout-options: workout ride unavailable: {e}")

        analysis_service = container.analysis_service
        if constraints.get('workout_type') == 'Group Ride' and analysis_service:
            try:
                target_weekday = _date.today().weekday()
                group_rides = analysis_service.find_group_rides_for_day(
                    target_weekday=target_weekday,
                    min_duration_minutes=constraints.get('min_duration_minutes') or 30,
                    limit=3,
                )
                if group_rides:
                    best = group_rides[0]
                    options['group_ride'] = {
                        'name': best['name'],
                        'frequency': best['frequency'],
                        'avg_duration_minutes': best['avg_duration_minutes'],
                        'avg_distance_miles': best['avg_distance_miles'],
                        'latest_date': best['latest_date'],
                        'alternatives': group_rides[1:],
                    }
            except Exception as e:
                logger.warning(f"Workout-options: group ride lookup failed: {e}")

        options['indoor'] = {
            'duration_minutes': constraints.get('min_duration_minutes'),
            'notes': 'Full workout as prescribed',
        }

        return jsonify({
            'status': 'success',
            'workout': workout_info,
            'weather_suitable': weather_suitable,
            'indoor_reason': indoor_reason,
            'options': options,
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting workout options: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@bp.route('/commute/map')
def get_commute_map():
    """Get interactive map HTML showing both commute routes."""
    container = current_app.container
    container.initialise()

    commute_service = container.commute_service
    if commute_service is None:
        return jsonify({'status': 'error', 'message': 'Commute is currently unavailable'}), 503

    try:
        from src.config_manager import ConfigManager
        from src.location_finder import Location

        to_work = commute_service.get_next_commute(direction='to_work')
        to_home = commute_service.get_next_commute(direction='to_home')

        routes = []
        if to_work.get('status') == 'success':
            to_work['direction'] = 'to_work'
            routes.append(to_work)
        if to_home.get('status') == 'success':
            to_home['direction'] = 'to_home'
            routes.append(to_home)

        if not routes:
            return jsonify({'status': 'error', 'message': 'No commute routes available'}), 404

        config = ConfigManager.get_instance()
        try:
            home_lat = config.get('location.home.latitude')
            home_lon = config.get('location.home.longitude')
            work_lat = config.get('location.work.latitude')
            work_lon = config.get('location.work.longitude')
            if None in (home_lat, home_lon, work_lat, work_lon):
                raise ValueError("Missing location coordinates in config")
            home_location = Location(lat=float(home_lat), lon=float(home_lon), name="Home", activity_count=0)
            work_location = Location(lat=float(work_lat), lon=float(work_lon), name="Work", activity_count=0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid location coordinates in config: {exc}")

        map_html = commute_service.generate_comparison_map(
            routes=routes,
            home_location=home_location,
            work_location=work_location
        )

        if map_html:
            return map_html, 200, {'Content-Type': 'text/html'}
        else:
            return jsonify({'status': 'error', 'message': 'Failed to generate map'}), 500

    except Exception as e:
        logger.error(f"Error generating commute map: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
