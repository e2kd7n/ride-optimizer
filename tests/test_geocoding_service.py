"""
Tests for app/services/geocoding_service.py.

Focus: US-biased lookup with fallback to unrestricted global search (#534).
"""

from unittest.mock import Mock, patch

from geopy.exc import GeocoderTimedOut

from app.services.geocoding_service import GeocodingService, _build_short_name


@patch('app.services.geocoding_service.Nominatim')
def _make_service(mock_nominatim):
    service = GeocodingService()
    service._geolocator = Mock()
    return service


def _make_location(lat=41.7, lon=-87.55, address='Big Marsh, Chicago, IL', addressdetails=None):
    loc = Mock()
    loc.latitude = lat
    loc.longitude = lon
    loc.address = address
    loc.raw = {'address': addressdetails or {}}
    return loc


def test_geocode_prefers_us_restricted_result():
    """A US-restricted hit should be returned without a second, unrestricted call."""
    service = _make_service()
    us_result = _make_location()
    service._geolocator.geocode.return_value = us_result

    result = service.geocode('Big Marsh')

    assert result['status'] == 'success'
    assert result['lat'] == 41.7
    assert service._geolocator.geocode.call_count == 1
    _, kwargs = service._geolocator.geocode.call_args
    assert kwargs['country_codes'] == 'us'


def test_geocode_falls_back_to_global_when_us_restricted_finds_nothing():
    """An explicit foreign query should still resolve via the unrestricted fallback."""
    service = _make_service()
    global_result = _make_location(lat=45.1, lon=-64.3, address='Big Marsh, Nova Scotia, Canada')
    service._geolocator.geocode.side_effect = [None, global_result]

    result = service.geocode('Big Marsh, Nova Scotia')

    assert result['status'] == 'success'
    assert result['lat'] == 45.1
    assert service._geolocator.geocode.call_count == 2
    first_kwargs = service._geolocator.geocode.call_args_list[0][1]
    second_kwargs = service._geolocator.geocode.call_args_list[1][1]
    assert first_kwargs['country_codes'] == 'us'
    assert 'country_codes' not in second_kwargs


def test_geocode_returns_error_when_nothing_found():
    service = _make_service()
    service._geolocator.geocode.side_effect = [None, None]

    result = service.geocode('Nowhere Place Xyzzy')

    assert result['status'] == 'error'
    assert 'No location found' in result['message']


def test_geocode_handles_geocoder_error():
    service = _make_service()
    service._geolocator.geocode.side_effect = GeocoderTimedOut('timed out')

    result = service.geocode('Big Marsh')

    assert result['status'] == 'error'
    assert 'unavailable' in result['message']


def test_build_short_name_with_house_number_city_state():
    address = {
        'house_number': '123',
        'road': 'Main St',
        'city': 'Chicago',
        'state': 'Illinois',
    }
    assert _build_short_name(address) == '123 Main St, Chicago, IL'


def test_build_short_name_empty_address():
    assert _build_short_name({}) is None
