"""Tests for app/container.py — ServiceContainer lazy accessors (#572).

get_exploration_service() lazily constructs ExplorationService on first
access. Without a lock, concurrent first-requests could each observe
`exploration_service` as None and construct their own instance, silently
discarding one of them (and its CoverageTracker's in-memory state).
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.container import ServiceContainer


@pytest.mark.unit
class TestGetExplorationServiceLocking:
    def test_returns_same_instance_on_repeated_calls(self):
        container = ServiceContainer()
        with patch("app.services.exploration_service.ExplorationService") as mock_cls:
            mock_cls.return_value = MagicMock(name="exploration_service_instance")
            first = container.get_exploration_service()
            second = container.get_exploration_service()
        assert first is second
        mock_cls.assert_called_once()

    def test_concurrent_first_access_constructs_only_once(self):
        """Regression for #572: two threads racing the first call must not
        each construct their own ExplorationService."""
        container = ServiceContainer()
        construct_count = 0
        construct_lock = threading.Lock()

        def slow_constructor(*args, **kwargs):
            nonlocal construct_count
            with construct_lock:
                construct_count += 1
            # Widen the race window so both threads are highly likely to
            # observe exploration_service as None before either finishes
            # constructing, if the lock weren't there.
            time.sleep(0.05)
            return MagicMock(name="exploration_service_instance")

        results = []

        def call_getter():
            results.append(container.get_exploration_service())

        with patch(
            "app.services.exploration_service.ExplorationService",
            side_effect=slow_constructor,
        ):
            threads = [threading.Thread(target=call_getter) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

        assert construct_count == 1
        assert len(results) == 8
        assert all(r is results[0] for r in results)

    def test_existing_service_short_circuits_without_reconstructing(self):
        container = ServiceContainer()
        sentinel = MagicMock(name="already_built")
        container.exploration_service = sentinel

        with patch("app.services.exploration_service.ExplorationService") as mock_cls:
            result = container.get_exploration_service()

        assert result is sentinel
        mock_cls.assert_not_called()

    def test_first_construction_triggers_prewarm(self):
        """#560: the container should kick off the exploration service's
        cold-start pre-warm right after constructing it."""
        container = ServiceContainer()
        with patch("app.services.exploration_service.ExplorationService") as mock_cls:
            mock_instance = MagicMock(name="exploration_service_instance")
            mock_cls.return_value = mock_instance
            container.get_exploration_service()

        mock_instance.start_prewarm.assert_called_once()

    def test_repeated_access_does_not_retrigger_prewarm(self):
        container = ServiceContainer()
        with patch("app.services.exploration_service.ExplorationService") as mock_cls:
            mock_instance = MagicMock(name="exploration_service_instance")
            mock_cls.return_value = mock_instance
            container.get_exploration_service()
            container.get_exploration_service()
            container.get_exploration_service()

        mock_instance.start_prewarm.assert_called_once()
