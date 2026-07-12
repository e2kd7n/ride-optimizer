"""
Unit tests for launch.py API endpoints.
"""

import pytest
import launch


@pytest.mark.unit
class TestLaunchAPIEndpoints:
    """Test suite for Smart Static API endpoints in launch.py."""

    def test_index_route(self, client):
        """Test index route serves static content."""
        response = client.get('/')
        assert response.status_code in [200, 404]

    def test_weather_endpoint_with_params(self, client, mock_services):
        """Test /api/weather with explicit lat/lon parameters."""
        mock_services['weather'].get_current_weather.return_value = {
            'temperature_f': 72,
            'feels_like_f': 70,
            'conditions': 'Clear',
            'wind_speed_kph': 16,
            'wind_direction_cardinal': 'NW',
            'humidity': 55,
            'precipitation_mm': 0,
            'comfort_score': 0.9
        }

        response = client.get('/api/weather?lat=40.7128&lon=-74.0060&location=NYC')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'current' in data
        assert data['current']['temperature'] == 72
        assert data['current']['comfort_score'] == 90

    def test_weather_endpoint_no_params_uses_home_location(self, client, mock_services):
        """Test /api/weather falls back to configured home location."""
        mock_services['weather'].get_current_weather.return_value = {
            'temperature_f': 68,
            'feels_like_f': 66,
            'conditions': 'Cloudy',
            'wind_speed_kph': 10,
            'wind_direction_cardinal': 'N',
            'humidity': 70,
            'precipitation_mm': 0.2,
            'comfort_score': 0.7
        }

        response = client.get('/api/weather')

        assert response.status_code == 200
        mock_services['weather'].get_current_weather.assert_called_once()
        args = mock_services['weather'].get_current_weather.call_args[0]
        assert args[0] == 40.7128
        assert args[1] == -74.0060

    def test_weather_endpoint_error(self, client, mock_services):
        """Test /api/weather error handling returns 500 with error status."""
        mock_services['weather'].get_current_weather.side_effect = Exception('API Error')

        response = client.get('/api/weather?lat=40.7128&lon=-74.0060')

        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'message' in data

    def test_recommendation_endpoint_formats_success_payload(self, client, mock_services):
        """Test /api/recommendation returns normalized frontend/API payload."""
        mock_services['commute'].get_next_commute.return_value = {
            'status': 'success',
            'direction': 'to_work',
            'time_window': 'morning',
            'is_today': True,
            'departure_time': '8:00 AM',
            'confidence': 'high',
            'route': {
                'id': 'route-1',
                'name': 'Main Route',
                'distance': 5.2,
                'duration': 25,
                'elevation': 45,
                'coordinates': [(40.7128, -74.0060), (40.7589, -73.9851)]
            },
            'score': 0.85,
            'breakdown': {
                'weather': 0.9,
                'time': 0.8
            },
            'weather': {
                'temperature': 72,
                'conditions': 'Clear'
            }
        }

        response = client.get('/api/recommendation')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['direction'] == 'to_work'
        assert data['score'] == 85
        assert data['recommended_route']['id'] == 'route-1'
        assert data['recommended_route']['distance'] == 5.2
        assert data['route']['name'] == 'Main Route'
        assert 'Weather: 90%' in data['factors']
        assert 'Time: 80%' in data['factors']

    def test_recommendation_with_direction(self, client, mock_services):
        """Test /api/recommendation forwards direction parameter."""
        mock_services['commute'].get_next_commute.return_value = {
            'status': 'error',
            'direction': 'to_home',
            'message': 'No routes available',
            'route': None
        }

        response = client.get('/api/recommendation?direction=to_home')

        assert response.status_code == 200
        mock_services['commute'].get_next_commute.assert_called_with('to_home')
        data = response.get_json()
        assert data['direction'] == 'to_home'

    def test_routes_endpoint(self, client, mock_services):
        """Test /api/routes endpoint."""
        mock_services['route_library'].get_all_routes.return_value = {
            'status': 'success',
            'routes': [
                {'id': '1', 'name': 'Route 1', 'distance': 5.0},
                {'id': '2', 'name': 'Route 2', 'distance': 6.5}
            ],
            'total_count': 2
        }

        response = client.get('/api/routes')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['routes']) == 2

    def test_routes_with_filters(self, client, mock_services):
        """Test /api/routes with filter parameters."""
        mock_services['route_library'].get_all_routes.return_value = {
            'status': 'success',
            'routes': []
        }

        response = client.get('/api/routes?type=commute&sort=distance&limit=10')

        assert response.status_code == 200
        mock_services['route_library'].get_all_routes.assert_called_with(
            route_type='commute',
            sort_by='distance',
            limit=10
        )

    def test_status_endpoint(self, client, mock_services):
        """Test /api/status endpoint."""
        mock_services['analysis'].get_analysis_status.return_value = {
            'has_data': True,
            'last_analysis': '2026-05-07T03:00:00',
            'activities_count': 150,
            'route_groups_count': 12,
            'long_rides_count': 8
        }

        response = client.get('/api/status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'services' in data
        assert 'data' in data

    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/api/nonexistent')

        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()


@pytest.mark.unit
class TestExplorationTilesAPI:
    """Tests for /api/exploration/tiles — squadrat/squadratinho coverage retrieval."""

    def test_default_zoom_is_squadrat(self, client):
        response = client.get('/api/exploration/tiles')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['zoom'] == 14

    def test_explicit_squadratinho_zoom(self, client):
        response = client.get('/api/exploration/tiles?zoom=17')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['zoom'] == 17

    def test_invalid_zoom_rejected(self, client):
        response = client.get('/api/exploration/tiles?zoom=20')
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'

    def test_bounded_request_with_zoom(self, client):
        response = client.get(
            '/api/exploration/tiles?south=41.0&west=-88.0&north=42.0&east=-87.0&zoom=17'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['zoom'] == 17
        assert data['bounds'] == [41.0, -88.0, 42.0, -87.0]


@pytest.mark.unit
class TestExplorationVerifyTilesAPI:
    """Tests for /api/exploration/verify-tiles (#493) — checks a planned
    route's real coordinates against the tiles it claims to reach."""

    def test_claims_tile_the_route_enters(self, client):
        from src.coverage_tracker import tile_to_bounds
        x, y, zoom = 4825, 6160, 14
        south, west, north, east = tile_to_bounds(x, y, zoom=zoom)
        inside_lon = west + (east - west) * 0.5

        response = client.post('/api/exploration/verify-tiles', json={
            'coordinates': [[south, inside_lon], [north, inside_lon]],
            'tiles': [{'x': x, 'y': y, 'zoom': zoom}],
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['claimed'] == [{'x': x, 'y': y, 'zoom': zoom}]

    def test_does_not_claim_tile_route_only_skirts(self, client):
        from src.coverage_tracker import tile_to_bounds
        x, y, zoom = 4825, 6160, 14
        south, west, north, east = tile_to_bounds(x, y, zoom=zoom)
        just_outside_lon = west - (east - west) * 0.001

        response = client.post('/api/exploration/verify-tiles', json={
            'coordinates': [[south, just_outside_lon], [north, just_outside_lon]],
            'tiles': [{'x': x, 'y': y, 'zoom': zoom}],
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['claimed'] == []

    def test_missing_coordinates_rejected(self, client):
        response = client.post('/api/exploration/verify-tiles', json={
            'tiles': [{'x': 1, 'y': 1, 'zoom': 14}],
        })
        assert response.status_code == 400

    def test_missing_tiles_rejected(self, client):
        response = client.post('/api/exploration/verify-tiles', json={
            'coordinates': [[40.0, -74.0]],
        })
        assert response.status_code == 400

    def test_invalid_zoom_rejected(self, client):
        response = client.post('/api/exploration/verify-tiles', json={
            'coordinates': [[40.0, -74.0]],
            'tiles': [{'x': 1, 'y': 1, 'zoom': 5}],
        })
        assert response.status_code == 400

    def test_oversized_coordinates_rejected(self, client):
        response = client.post('/api/exploration/verify-tiles', json={
            'coordinates': [[40.0, -74.0]] * 5001,
            'tiles': [{'x': 1, 'y': 1, 'zoom': 14}],
        })
        assert response.status_code == 400


@pytest.mark.unit
class TestSavedPlansAPI:
    """Tests for saved plans CRUD endpoints."""

    def test_get_plans_empty(self, client):
        response = client.get('/api/plans')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert isinstance(data['plans'], list)

    def test_save_plan(self, client):
        response = client.post('/api/plans', json={
            'route_id': 'test-route-1',
            'route_name': 'Morning Loop',
            'route_type': 'commute',
            'distance': 15.5,
            'duration': 45,
            'elevation': 120,
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['plan']['route_id'] == 'test-route-1'
        assert data['plan']['route_name'] == 'Morning Loop'
        assert 'id' in data['plan']
        assert 'created_at' in data['plan']

    def test_save_plan_requires_route_id(self, client):
        response = client.post('/api/plans', json={'route_name': 'No ID'})
        assert response.status_code == 400

    def test_save_and_delete_plan(self, client):
        create_resp = client.post('/api/plans', json={
            'route_id': 'delete-me',
            'route_name': 'Temp Plan',
        })
        plan_id = create_resp.get_json()['plan']['id']

        delete_resp = client.delete(f'/api/plans/{plan_id}')
        assert delete_resp.status_code == 200
        assert delete_resp.get_json()['status'] == 'success'

    def test_delete_nonexistent_plan(self, client):
        response = client.delete('/api/plans/nonexistent123')
        assert response.status_code == 404

    def test_save_plan_note_too_long(self, client):
        response = client.post('/api/plans', json={
            'route_id': 'test',
            'note': 'x' * 501,
        })
        assert response.status_code == 400


@pytest.mark.unit
class TestHourlyForecastAPI:
    """Tests for /api/weather/hourly endpoint."""

    def test_hourly_forecast_returns_expected_structure(self, client, mock_services):
        mock_services['weather'].fetcher.get_hourly_forecast.return_value = [
            {
                'timestamp': '2026-06-21T07:00',
                'temp_c': 20.0,
                'wind_speed_kph': 15.0,
                'wind_gust_kph': 20.0,
                'wind_direction_deg': 180,
                'precipitation_prob': 10,
            },
            {
                'timestamp': '2026-06-21T08:00',
                'temp_c': 22.0,
                'wind_speed_kph': 12.0,
                'wind_gust_kph': 16.0,
                'wind_direction_deg': 200,
                'precipitation_prob': 5,
            },
            {
                'timestamp': '2026-06-21T12:00',
                'temp_c': 28.0,
                'wind_speed_kph': 10.0,
                'wind_gust_kph': 14.0,
                'wind_direction_deg': 220,
                'precipitation_prob': 0,
            },
        ]

        response = client.get('/api/weather/hourly')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['hours']) == 3
        assert data['commute_hours']['morning'] == [7, 8]
        assert data['commute_hours']['evening'] == [16, 17, 18]

        h0 = data['hours'][0]
        assert h0['time'] == '07:00'
        assert h0['hour'] == 7
        assert h0['temp_f'] == 68
        assert h0['is_commute_hour'] is True

        h2 = data['hours'][2]
        assert h2['hour'] == 12
        assert h2['is_commute_hour'] is False

    def test_hourly_forecast_unavailable(self, client, mock_services):
        mock_services['weather'].fetcher.get_hourly_forecast.return_value = None
        response = client.get('/api/weather/hourly')
        assert response.status_code == 503

    def test_hourly_forecast_with_explicit_coords(self, client, mock_services):
        mock_services['weather'].fetcher.get_hourly_forecast.return_value = []
        response = client.get('/api/weather/hourly?lat=51.5&lon=-0.1')
        mock_services['weather'].fetcher.get_hourly_forecast.assert_called_once_with(
            51.5, -0.1, hours=12
        )


@pytest.mark.unit
class TestDeleteUserData:
    """Tests for GDPR-compliant data deletion endpoint."""

    def test_delete_requires_confirmation(self, client):
        response = client.delete('/api/user/data', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'confirm' in data['message'].lower()

    def test_delete_rejects_false_confirmation(self, client):
        response = client.delete('/api/user/data', json={'confirm': False})
        assert response.status_code == 400

    def test_delete_succeeds_with_confirmation(self, client, tmp_path, monkeypatch):
        from pathlib import Path
        from src.json_storage import JSONStorage
        from launch import app
        test_storage = JSONStorage(str(tmp_path))
        test_storage.write('test_data.json', {'key': 'value'})
        monkeypatch.setattr(app.container, 'storage', test_storage)

        fake_creds = tmp_path / 'credentials.json'
        fake_creds.write_text('{}')
        monkeypatch.setattr(app.container, 'credentials_path', fake_creds)

        # Regression guard: every path this endpoint unlinks must be derived
        # from the (mocked) container, never hardcoded — otherwise this test
        # deletes the real Strava cache/credentials on disk. See incident
        # where this silently wiped data/cache/activities.json for real.
        real_cache = Path('data/cache/activities.json')
        real_cache_existed_before = real_cache.exists()
        real_creds = Path('config/credentials.json')
        real_creds_existed_before = real_creds.exists()

        response = client.delete('/api/user/data', json={'confirm': True})
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert isinstance(data['deleted'], list)

        assert real_cache.exists() == real_cache_existed_before
        assert real_creds.exists() == real_creds_existed_before
        assert not fake_creds.exists()

    def test_delete_no_body_returns_400(self, client):
        response = client.delete('/api/user/data')
        assert response.status_code == 400


@pytest.mark.unit
class TestSettingsAPI:
    """Tests for user settings CRUD endpoints."""

    @pytest.fixture(autouse=True)
    def reset_settings(self, client):
        client.delete('/api/settings')
        yield

    def test_get_settings_returns_defaults(self, client):
        response = client.get('/api/settings')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['settings']['unit_system'] == 'imperial'
        assert data['settings']['show_elevation'] is True

    def test_put_settings_partial_update(self, client):
        response = client.put('/api/settings', json={
            'unit_system': 'metric',
            'show_elevation': False,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['settings']['unit_system'] == 'metric'
        assert data['settings']['show_elevation'] is False
        assert data['settings']['default_view'] == 'home'

    def test_put_settings_ignores_unknown_keys(self, client):
        response = client.put('/api/settings', json={
            'unit_system': 'metric',
            'evil_key': 'hacked',
        })
        assert response.status_code == 200
        assert 'evil_key' not in response.get_json()['settings']

    def test_put_settings_validates_types(self, client):
        client.delete('/api/settings')
        response = client.put('/api/settings', json={'show_elevation': 'not-a-bool'})
        assert response.status_code == 200
        assert response.get_json()['settings']['show_elevation'] is True

    def test_delete_settings_resets(self, client):
        client.put('/api/settings', json={'unit_system': 'metric'})
        response = client.delete('/api/settings')
        assert response.status_code == 200
        assert response.get_json()['settings']['unit_system'] == 'imperial'

    def test_put_settings_empty_body_noop(self, client):
        response = client.put('/api/settings', data='not json', content_type='text/plain')
        assert response.status_code == 200
        assert response.get_json()['settings']['unit_system'] == 'imperial'


@pytest.mark.unit
class TestGracefulDegradation:
    """Test that endpoints return 503 when their service is unavailable."""

    def _set_null_service(self, client, attr):
        """Set a service to None on the app container and keep _initialised=True."""
        container = client.application.container
        setattr(container, attr, None)
        container._initialised = True

    def test_status_reports_service_health(self, client, mock_services):
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'services' in data
        for svc in ('analysis', 'commute', 'weather', 'planner', 'route_library', 'trainerroad'):
            assert svc in data['services']
            assert data['services'][svc] in ('available', 'unavailable')

    def test_status_reports_available_services(self, client, mock_services):
        response = client.get('/api/status')
        data = response.get_json()
        assert data['services']['analysis'] == 'available'
        assert data['services']['weather'] == 'available'
        assert data['services']['commute'] == 'available'

    def test_weather_503_when_service_unavailable(self, client, mock_services):
        self._set_null_service(client, 'weather_service')
        response = client.get('/api/weather?lat=40.7&lon=-74.0')
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Weather' in data['message']

    def test_recommendation_503_when_service_unavailable(self, client, mock_services):
        self._set_null_service(client, 'commute_service')
        response = client.get('/api/recommendation')
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Commute' in data['message']

    def test_routes_503_when_service_unavailable(self, client, mock_services):
        self._set_null_service(client, 'route_library_service')
        response = client.get('/api/routes')
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Route Library' in data['message']

    def test_trainerroad_503_when_service_unavailable(self, client, mock_services):
        self._set_null_service(client, 'trainerroad_service')
        response = client.get('/api/trainerroad/status')
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'TrainerRoad' in data['message']

    def test_analysis_503_when_unavailable(self, client, mock_services):
        self._set_null_service(client, 'analysis_service')
        response = client.get('/api/status')
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Analysis' in data['message']


@pytest.mark.integration
class TestLaunchInitialization:
    """Light integration coverage for service initialization."""

    def test_initialize_services_uses_existing_flag(self):
        """Test container.initialise() is idempotent when already initialized."""
        from launch import app
        container = app.container
        container._initialised = True
        container.initialise()  # should not re-run init
        assert container._initialised is True

