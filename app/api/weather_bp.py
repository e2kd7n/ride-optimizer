"""Weather API Blueprint.

Routes:
  GET /api/weather
  GET /api/weather/commute-windows
  GET /api/weather/hourly
  GET /api/weather/forecast
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from src.config_manager import ConfigManager
from src.secure_logger import SecureLogger
from app.schemas import WeatherQuerySchema, validate_request_args

logger = SecureLogger(__name__)

bp = Blueprint('weather', __name__, url_prefix='/api')


def _degrees_to_cardinal(deg: float) -> str:
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return dirs[round(deg / 22.5) % 16]


@bp.route('/weather')
@validate_request_args(WeatherQuerySchema)
def get_weather():
    """
    Get current weather data.

    Query params:
    - lat: Latitude (optional, defaults to home location)
    - lon: Longitude (optional, defaults to home location)
    - location: Location name (optional)
    """
    container = current_app.container
    container.initialise()

    weather_service = container.weather_service
    if weather_service is None:
        return jsonify({'status': 'error', 'message': 'Weather is currently unavailable'}), 503

    try:
        config = ConfigManager.get_instance()
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        location_name = request.args.get('location')

        if lat is None or lon is None:
            home_lat = config.get('location.home.latitude')
            home_lon = config.get('location.home.longitude')

            if home_lat and home_lon:
                lat, lon = home_lat, home_lon
                location_name = location_name or 'Home'
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'No location specified and no home location configured'
                }), 400

        weather_data = weather_service.get_current_weather(lat, lon, location_name)

        if weather_data:
            wind_speed_mph = weather_data.get('wind_speed_kph', 0) * 0.621371
            temp_c = weather_data.get('temp_c', 0) or 0
            feels_like_c = weather_data.get('feels_like_c', temp_c) or temp_c
            formatted_weather = {
                'temperature': round(weather_data.get('temperature_f', temp_c * 9/5 + 32)),
                'feels_like': round(weather_data.get('feels_like_f', feels_like_c * 9/5 + 32)),
                'conditions': weather_data.get('conditions', 'Unknown'),
                'description': weather_data.get('conditions', 'Unknown'),
                'wind_speed': round(wind_speed_mph),
                'wind_direction': weather_data.get('wind_direction_cardinal', 'N'),
                'humidity': weather_data.get('humidity', 0),
                'precipitation_probability': weather_data.get('precipitation_mm', 0),
                'comfort_score': int(weather_data.get('comfort_score', 0.5) * 100)
            }
            return jsonify({
                'status': 'success',
                'current': formatted_weather,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'status': 'error', 'message': 'Weather data unavailable'}), 503

    except Exception as e:
        logger.error(f"Error getting weather: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Weather data temporarily unavailable'}), 500


@bp.route('/weather/commute-windows')
def get_commute_windows():
    """
    Get hourly weather forecast sliced into morning and evening commute windows.

    Returns morning (7–9 AM) and evening (3–6 PM) conditions plus an optimal
    departure suggestion for each window.
    """
    container = current_app.container
    container.initialise()

    weather_service = container.weather_service
    if weather_service is None:
        return jsonify({'status': 'error', 'message': 'Weather is currently unavailable'}), 503

    try:
        config = ConfigManager.get_instance()
        lat = config.get('location.home.latitude')
        lon = config.get('location.home.longitude')
        if not lat or not lon:
            return jsonify({'status': 'error', 'message': 'Home location not configured'}), 400

        lat, lon = float(lat), float(lon)
        hourly = weather_service.fetcher.get_hourly_forecast(lat, lon, hours=24)
        if not hourly:
            return jsonify({'status': 'error', 'message': 'Forecast unavailable'}), 503

        def _format_hour(h: dict) -> dict:
            temp_f = round(h['temp_c'] * 9 / 5 + 32)
            wind_mph = round(h['wind_speed_kph'] * 0.621371)
            gust_mph = round(h.get('wind_gust_kph', h['wind_speed_kph']) * 0.621371)
            wind_deg = h.get('wind_direction_deg', 0)
            return {
                'hour': h['timestamp'][11:16],
                'temp_f': temp_f,
                'wind_mph': wind_mph,
                'wind_gust_mph': gust_mph,
                'wind_direction': _degrees_to_cardinal(wind_deg),
                'precip_prob': h.get('precipitation_prob', 0),
            }

        def _window_summary(hours: list) -> dict:
            if not hours:
                return {}
            avg_temp = round(sum(h['temp_f'] for h in hours) / len(hours))
            avg_wind = round(sum(h['wind_mph'] for h in hours) / len(hours))
            max_precip = max(h['precip_prob'] for h in hours)
            best = min(hours, key=lambda h: h['precip_prob'] * 2 + h['wind_mph'])
            dirs = [h['wind_direction'] for h in hours]
            dominant_dir = max(set(dirs), key=dirs.count)
            return {
                'avg_temp_f': avg_temp,
                'avg_wind_mph': avg_wind,
                'max_precip_prob': max_precip,
                'dominant_wind_direction': dominant_dir,
                'optimal_departure': best['hour'],
                'hours': hours,
            }

        morning_raw, evening_raw = [], []
        for h in hourly:
            ts = h.get('timestamp', '')
            try:
                hour_int = int(ts[11:13])
            except (ValueError, IndexError):
                continue
            if 7 <= hour_int <= 8:
                morning_raw.append(_format_hour(h))
            elif 15 <= hour_int <= 17:
                evening_raw.append(_format_hour(h))

        return jsonify({
            'status': 'success',
            'morning': _window_summary(morning_raw),
            'evening': _window_summary(evening_raw),
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting commute windows: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Forecast data temporarily unavailable'}), 500


@bp.route('/weather/hourly')
def get_hourly_forecast():
    """Get 12-hour hourly weather forecast with commute hours highlighted."""
    container = current_app.container
    container.initialise()

    weather_service = container.weather_service
    if not weather_service:
        return jsonify({'status': 'error', 'message': 'Weather service unavailable'}), 503

    try:
        config = ConfigManager.get_instance()
        lat = request.args.get('lat') or config.get('location.home.latitude')
        lon = request.args.get('lon') or config.get('location.home.longitude')
        if not lat or not lon:
            return jsonify({'status': 'error', 'message': 'Home location not configured'}), 400

        lat, lon = float(lat), float(lon)
        hourly = weather_service.fetcher.get_hourly_forecast(lat, lon, hours=12)
        if not hourly:
            return jsonify({'status': 'error', 'message': 'Forecast unavailable'}), 503

        morning_commute = {7, 8}
        evening_commute = {16, 17, 18}

        hours = []
        for h in hourly:
            ts = h.get('timestamp', '')
            try:
                hour_int = int(ts[11:13])
            except (ValueError, IndexError):
                continue
            temp_f = round(h['temp_c'] * 9 / 5 + 32)
            wind_mph = round(h['wind_speed_kph'] * 0.621371)
            hours.append({
                'time': ts[11:16],
                'hour': hour_int,
                'temp_f': temp_f,
                'temp_c': round(h['temp_c']),
                'wind_speed_mph': wind_mph,
                'wind_speed_kph': round(h['wind_speed_kph']),
                'precipitation_prob': h.get('precipitation_prob', 0),
                'is_commute_hour': hour_int in morning_commute or hour_int in evening_commute,
            })

        return jsonify({
            'status': 'success',
            'hours': hours,
            'commute_hours': {
                'morning': sorted(morning_commute),
                'evening': sorted(evening_commute),
            },
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting hourly forecast: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Forecast data temporarily unavailable'}), 500


@bp.route('/weather/forecast')
def get_weather_forecast():
    """Get 7-day daily weather forecast."""
    container = current_app.container
    container.initialise()

    weather_service = container.weather_service
    if weather_service is None:
        return jsonify({'status': 'error', 'message': 'Weather is currently unavailable'}), 503

    try:
        config = ConfigManager.get_instance()
        lat = config.get('location.home.latitude')
        lon = config.get('location.home.longitude')
        if not lat or not lon:
            return jsonify({'status': 'error', 'message': 'Home location not configured'}), 400

        lat, lon = float(lat), float(lon)
        raw = weather_service.fetcher.get_daily_forecast(lat, lon, days=7)
        if not raw:
            return jsonify({'status': 'error', 'message': 'Forecast unavailable'}), 503

        def _comfort(day: dict) -> float:
            temp_c = (day.get('temp_max_c', 20) + day.get('temp_min_c', 15)) / 2
            score = 1.0
            if temp_c < 0:
                score -= 0.4
            elif temp_c < 10:
                score -= 0.2
            elif temp_c > 35:
                score -= 0.5
            elif temp_c > 30:
                score -= 0.3
            wind = day.get('wind_speed_max_kph', 0) or 0
            if wind > 30:
                score -= 0.3
            elif wind > 20:
                score -= 0.15
            precip = day.get('precipitation_sum_mm', 0) or 0
            if precip > 5:
                score -= 0.4
            elif precip > 0:
                score -= 0.2
            return round(max(0.0, min(1.0, score)), 2)

        def _favorability(score: float) -> str:
            if score >= 0.7:
                return 'favorable'
            elif score >= 0.4:
                return 'neutral'
            return 'unfavorable'

        days = []
        for day in raw:
            comfort = _comfort(day)
            temp_max_f = round(day.get('temp_max_c', 20) * 9 / 5 + 32)
            temp_min_f = round(day.get('temp_min_c', 15) * 9 / 5 + 32)
            wind_mph = round((day.get('wind_speed_max_kph', 0) or 0) * 0.621371)
            wind_dir = _degrees_to_cardinal(day.get('wind_direction_dominant_deg', 0) or 0)
            precip_prob = day.get('precipitation_prob_max', 0) or 0
            precip_in = round((day.get('precipitation_sum_mm', 0) or 0) * 0.0393701, 2)
            days.append({
                'date': day.get('date'),
                'temp_max_f': temp_max_f,
                'temp_min_f': temp_min_f,
                'wind_mph': wind_mph,
                'wind_direction': wind_dir,
                'precip_prob': precip_prob,
                'precip_in': precip_in,
                'comfort_score': int(comfort * 100),
                'cycling_favorability': _favorability(comfort),
            })

        return jsonify({
            'status': 'success',
            'forecast': days,
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Forecast data temporarily unavailable'}), 500
