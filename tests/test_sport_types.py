"""Shared sport classification and Garmin type mapping (#622)."""
from types import SimpleNamespace

import pytest

from src.data_fetcher import Activity
from src.sport_types import activity_class, garmin_sport_type


@pytest.mark.unit
@pytest.mark.parametrize('sport,cls', [
    ('Ride', 'cycling'), ('GravelRide', 'cycling'), ('MountainBikeRide', 'cycling'),
    ('VirtualRide', 'cycling'), ('EBikeRide', 'cycling'),
    ('Run', 'running'), ('TrailRun', 'running'),
    ('Walk', 'other'), ('Swim', 'other'), ('Workout', 'other'), ('', 'other'),
])
def test_activity_class(sport, cls):
    assert activity_class(SimpleNamespace(sport_type=sport, type=sport)) == cls


@pytest.mark.unit
def test_sport_type_wins_over_type():
    assert activity_class(SimpleNamespace(sport_type='GravelRide', type='Ride')) == 'cycling'
    assert activity_class(SimpleNamespace(sport_type=None, type='Run')) == 'running'


@pytest.mark.unit
@pytest.mark.parametrize('key,sport', [
    ('road_biking', 'Ride'), ('gravel_cycling', 'GravelRide'),
    ('mountain_biking', 'MountainBikeRide'), ('indoor_cycling', 'VirtualRide'),
    ('lap_swimming', 'Swim'), ('strength_training', 'WeightTraining'),
    ('some_new_cycling_kind', 'Ride'), ('street_running', 'Run'),
    ('breathwork', 'Workout'), ('', 'Workout'),
])
def test_garmin_sport_type(key, sport):
    assert garmin_sport_type(key) == sport


@pytest.mark.unit
def test_garmin_unknown_type_is_no_longer_a_ride():
    a = Activity.from_garmin_activity({'activityId': 1, 'activityType': {'typeKey': 'lap_swimming'}})
    assert (a.type, a.sport_type) == ('Swim', 'Swim')


@pytest.mark.unit
def test_garmin_mountain_bike_keeps_broad_ride_type():
    a = Activity.from_garmin_activity({'activityId': 1, 'activityType': {'typeKey': 'mountain_biking'}})
    assert (a.type, a.sport_type) == ('Ride', 'MountainBikeRide')
