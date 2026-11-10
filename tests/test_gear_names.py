"""Gear cache protection and local gear names (#623)."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.data_fetcher import StravaDataFetcher


@pytest.fixture
def fetcher(tmp_path):
    f = StravaDataFetcher(MagicMock(), MagicMock(), use_test_cache=False)
    f.cache_path = tmp_path / 'activities.json'
    return f


def _write_gear(f, bikes, shoes=()):
    f._gear_cache_path.write_text(json.dumps({'bikes': list(bikes), 'shoes': list(shoes)}))


ROAD = {'id': 'b1', 'name': 'Road Bike', 'type': 'bike', 'brand_name': 'Trek',
        'model_name': 'Domane', 'primary': True, 'strava_distance_m': 1000.0}


@pytest.mark.unit
class TestEmptyProfileDoesNotWipeCache:
    def test_empty_response_keeps_existing(self, fetcher):
        _write_gear(fetcher, [ROAD])
        fetcher.client.get_athlete.return_value = SimpleNamespace(bikes=[], shoes=[])
        data = fetcher.fetch_athlete_gear()
        assert data['kept_previous'] is True
        assert json.loads(fetcher._gear_cache_path.read_text())['bikes'][0]['name'] == 'Road Bike'

    def test_empty_response_with_no_cache_is_written(self, fetcher):
        fetcher.client.get_athlete.return_value = SimpleNamespace(bikes=None, shoes=None)
        data = fetcher.fetch_athlete_gear()
        assert data['bikes'] == [] and 'kept_previous' not in data
        assert fetcher._gear_cache_path.exists()

    def test_real_gear_replaces_cache(self, fetcher):
        _write_gear(fetcher, [ROAD])
        bike = SimpleNamespace(id='b9', name='Gravel', distance=5.0, primary=False,
                               brand_name='', model_name='')
        fetcher.client.get_athlete.return_value = SimpleNamespace(bikes=[bike], shoes=[])
        fetcher.fetch_athlete_gear()
        assert [b['id'] for b in json.loads(fetcher._gear_cache_path.read_text())['bikes']] == ['b9']


@pytest.mark.unit
class TestLocalGearNames:
    def test_none_without_cache_or_names(self, fetcher):
        assert fetcher.load_cached_gear() is None

    def test_local_name_overrides_and_adds(self, fetcher):
        _write_gear(fetcher, [ROAD, {'id': 'b2', 'name': '', 'type': 'bike'}])
        fetcher.save_gear_names({'b2': {'name': 'Commuter', 'type': 'bike'},
                                 'g3': {'name': 'Trail shoes', 'type': 'shoe'}})
        gear = fetcher.load_cached_gear()
        by_id = {g['id']: g for g in gear['bikes'] + gear['shoes']}
        assert by_id['b1']['name'] == 'Road Bike'
        assert by_id['b2']['name'] == 'Commuter' and by_id['b2']['name_source'] == 'local'
        assert by_id['g3']['type'] == 'shoe' and by_id['g3'] in gear['shoes']

    def test_names_alone_make_gear_available(self, fetcher):
        """The Pi's case: gear.json emptied, rides only carry raw IDs."""
        _write_gear(fetcher, [])
        fetcher.save_gear_names({'b7': {'name': 'Old faithful', 'type': 'bike'}})
        assert fetcher.load_cached_gear()['bikes'][0]['name'] == 'Old faithful'

    def test_blank_name_removes_entry(self, fetcher):
        fetcher.save_gear_names({'b2': {'name': 'Commuter', 'type': 'bike'}})
        fetcher.save_gear_names({'b2': {'name': '  ', 'type': 'bike'}})
        assert fetcher.load_gear_names() == {}


@pytest.mark.unit
class TestGearNamesEndpoint:
    @pytest.fixture
    def svc(self, client, monkeypatch, tmp_path):
        from launch import app
        f = StravaDataFetcher(MagicMock(), MagicMock(), use_test_cache=False)
        f.cache_path = tmp_path / 'activities.json'
        analysis = MagicMock()
        analysis.cache_fetcher = f
        monkeypatch.setattr(app.container, '_initialised', True)
        monkeypatch.setattr(app.container, 'analysis_service', analysis)
        return f

    def test_round_trip(self, client, svc):
        resp = client.put('/api/gear/names', json={'names': {'b1': {'name': 'Road', 'type': 'bike'}}})
        assert resp.status_code == 200
        assert client.get('/api/gear/names').get_json()['names'] == {'b1': {'name': 'Road', 'type': 'bike'}}

    @pytest.mark.parametrize('body', [
        {'names': {'../x': {'name': 'a'}}},
        {'names': {'b1': {'name': 'a', 'type': 'car'}}},
        {'names': {'b1': {'name': 'x' * 61}}},
        {'names': []},
    ])
    def test_rejects_bad_input(self, client, svc, body):
        assert client.put('/api/gear/names', json=body).status_code == 400

    def test_gear_stats_use_local_names(self, client, svc, monkeypatch):
        from app.api import stats_bp
        from src.data_fetcher import Activity
        act = Activity(id=1, name='Morning Ride', type='Ride', sport_type='Ride',
                       start_date='2026-09-01T13:00:00Z', start_date_local='2026-09-01T08:00:00Z',
                       distance=16093.4, moving_time=3600, elapsed_time=3600,
                       total_elevation_gain=100.0, average_speed=4.47,
                       start_latlng=None, end_latlng=None, polyline=None, gear_id='b5')
        monkeypatch.setattr(stats_bp, '_load_activities_for_stats', lambda: [act])
        svc.save_gear_names({'b5': {'name': 'Rain bike', 'type': 'bike'}})
        gear = client.get('/api/stats/gear').get_json()['data']['gear']
        assert gear[0]['name'] == 'Rain bike'
