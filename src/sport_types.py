"""Activity sport classification shared across the app (#622).

Strava sport types (and Garmin activities mapped onto them in
``Activity.from_garmin_activity``) grouped into the classes the chat tools
filter by. Keep new cycling types here so every consumer agrees.
"""

from typing import Any

CYCLING_TYPES = frozenset({
    'Ride', 'GravelRide', 'MountainBikeRide', 'EBikeRide', 'EMountainBikeRide',
    'VirtualRide', 'Velomobile', 'Handcycle',
})
RUNNING_TYPES = frozenset({'Run', 'TrailRun', 'VirtualRun'})

ACTIVITY_CLASSES = ('cycling', 'running', 'other', 'all')


def sport_of(activity: Any) -> str:
    """The most specific sport type an activity carries."""
    return getattr(activity, 'sport_type', None) or getattr(activity, 'type', None) or ''


def activity_class(activity: Any) -> str:
    sport = sport_of(activity)
    if sport in CYCLING_TYPES:
        return 'cycling'
    if sport in RUNNING_TYPES:
        return 'running'
    return 'other'


def garmin_sport_type(type_key: str) -> str:
    """Map a Garmin ``activityType.typeKey`` to a Strava sport type.

    Unknown keys used to default to 'Ride', so swims, strength sessions and
    yoga landed in the cache as rides. Now only keys that look like cycling
    become rides; everything else is a generic 'Workout'.
    """
    key = (type_key or '').lower()
    exact = {
        'cycling': 'Ride',
        'road_biking': 'Ride',
        'gravel_cycling': 'GravelRide',
        'mountain_biking': 'MountainBikeRide',
        'e_bike_mountain': 'EMountainBikeRide',
        'e_bike_fitness': 'EBikeRide',
        'virtual_ride': 'VirtualRide',
        'indoor_cycling': 'VirtualRide',
        'running': 'Run',
        'treadmill_running': 'Run',
        'trail_running': 'TrailRun',
        'virtual_run': 'VirtualRun',
        'walking': 'Walk',
        'hiking': 'Hike',
        'lap_swimming': 'Swim',
        'open_water_swimming': 'Swim',
        'swimming': 'Swim',
        'strength_training': 'WeightTraining',
        'yoga': 'Yoga',
        'rowing': 'Rowing',
        'indoor_rowing': 'Rowing',
        'kayaking_v2': 'Kayaking',
        'kayaking': 'Kayaking',
        'stand_up_paddleboarding': 'StandUpPaddling',
        'resort_skiing_snowboarding_ws': 'AlpineSki',
        'cross_country_skiing_ws': 'NordicSki',
    }
    if key in exact:
        return exact[key]
    if 'cycl' in key or 'bik' in key or 'ride' in key:
        return 'Ride'
    if 'run' in key:
        return 'Run'
    return 'Workout'
