"""Tests for ServiceContainer.refresh_services (issue #461).

reset_initialisation() forces a full re-init of every service on the next
initialise() call. refresh_services() should instead rebuild only the named
services in place, leaving the others untouched, and should be a no-op
before the container has completed its first initialise().
"""

from unittest.mock import MagicMock

import pytest

from app.container import ServiceContainer


@pytest.mark.unit
class TestRefreshServices:
    def test_noop_before_first_initialise(self):
        container = ServiceContainer()
        # Never called container.initialise() — _initialised is False.
        container._init_weather = MagicMock()
        container.refresh_services('weather')
        container._init_weather.assert_not_called()

    def test_only_named_services_are_rebuilt(self):
        container = ServiceContainer()
        container._initialised = True
        container._init_weather = MagicMock(name='init_weather')
        container._init_trainerroad = MagicMock(name='init_trainerroad')
        container._init_route_library = MagicMock(name='init_route_library')
        container._init_analysis = MagicMock(name='init_analysis')
        container._init_commute = MagicMock(name='init_commute')
        container._init_planner = MagicMock(name='init_planner')

        container.refresh_services('commute', 'planner')

        container._init_commute.assert_called_once()
        container._init_planner.assert_called_once()
        container._init_weather.assert_not_called()
        container._init_trainerroad.assert_not_called()
        container._init_route_library.assert_not_called()
        container._init_analysis.assert_not_called()

    def test_unknown_service_name_is_skipped_not_raised(self):
        container = ServiceContainer()
        container._initialised = True
        container._init_commute = MagicMock()

        container.refresh_services('not_a_real_service', 'commute')

        container._init_commute.assert_called_once()

    def test_exception_in_one_service_does_not_block_others(self):
        container = ServiceContainer()
        container._initialised = True
        container._init_commute = MagicMock(side_effect=RuntimeError("boom"))
        container._init_planner = MagicMock()

        container.refresh_services('commute', 'planner')

        container._init_planner.assert_called_once()

    def test_does_not_flip_initialised_flag(self):
        container = ServiceContainer()
        container._initialised = True
        container._init_commute = MagicMock()

        container.refresh_services('commute')

        assert container._initialised is True
