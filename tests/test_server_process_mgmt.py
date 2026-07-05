"""
Unit tests for launch.py server process-management helpers.

Tests:
  - _write_pid_file / _read_pid_file / _remove_pid_file
  - _is_our_server_process (mocked via psutil)
  - kill_existing_server  — PID-file path, port-scan fallback, stale-file cleanup
  - server_status         — running, not-running, stale PID file
  - stop_server           — happy path, nothing running, already-gone PID

These are pure unit tests: no real Flask server is started.
"""

import json
import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call


# ------------------------------------------------------------------ helpers --

def _import_helpers():
    """Import the process-management functions from launch.py at call time
    so that psutil (which may not be installed in CI) is only required here.
    """
    import importlib.util, sys

    # We import just the symbols we need without executing the Flask app setup.
    # launch.py guards heavy setup behind ``if __name__ == '__main__'`` so a
    # plain import is safe (the Flask app is created at module level, but that
    # is acceptable — it just won't receive requests in this context).
    import launch  # noqa: F401 — import side-effects are acceptable
    return launch


# ------------------------------------------------------------------ fixtures --

@pytest.fixture()
def tmp_pid_path(tmp_path, monkeypatch):
    """Redirect _pid_file_path() to a temp directory for isolation."""
    pid_file = str(tmp_path / 'ride-optimizer-server.pid')

    import launch
    monkeypatch.setattr(launch, '_pid_file_path', lambda: pid_file)
    return pid_file


# ============================================================ PID file I/O ==

@pytest.mark.unit
class TestPidFileIO:
    def test_write_and_read_round_trip(self, tmp_pid_path):
        import launch
        launch._write_pid_file(pid=12345, port=8083)

        data = launch._read_pid_file()
        assert data['pid'] == 12345
        assert data['port'] == 8083
        assert 'started' in data
        # started should be a parseable ISO timestamp
        datetime.fromisoformat(data['started'])

    def test_read_missing_file_returns_empty_dict(self, tmp_pid_path):
        import launch
        # File does not exist yet
        assert launch._read_pid_file() == {}

    def test_read_corrupt_file_returns_empty_dict(self, tmp_pid_path):
        import launch
        with open(tmp_pid_path, 'w') as fh:
            fh.write('not valid json{{{')
        assert launch._read_pid_file() == {}

    def test_remove_pid_file_deletes_file(self, tmp_pid_path):
        import launch
        launch._write_pid_file(pid=1, port=8083)
        assert os.path.exists(tmp_pid_path)
        launch._remove_pid_file()
        assert not os.path.exists(tmp_pid_path)

    def test_remove_pid_file_is_idempotent(self, tmp_pid_path):
        import launch
        # Should not raise even if the file is already absent
        launch._remove_pid_file()
        launch._remove_pid_file()


# ========================================= _is_our_server_process (mocked) ==

@pytest.mark.unit
class TestIsOurServerProcess:
    def _make_proc(self, cmdline, status='running'):
        proc = MagicMock()
        proc.status.return_value = status
        proc.cmdline.return_value = cmdline
        return proc

    def test_valid_launch_serve_process(self):
        import launch
        cmdline = ['/usr/bin/python', '/home/user/ride-optimizer/launch.py', '--serve', '8083']
        proc = self._make_proc(cmdline)
        with patch('psutil.Process', return_value=proc):
            assert launch._is_our_server_process(99999) is True

    def test_unrelated_process_returns_false(self):
        import launch
        proc = self._make_proc(['/usr/bin/python', 'some_other_script.py'])
        with patch('psutil.Process', return_value=proc):
            assert launch._is_our_server_process(99999) is False

    def test_zombie_process_returns_false(self):
        import launch
        import psutil
        cmdline = ['python', 'launch.py', '--serve', '8083']
        proc = self._make_proc(cmdline, status=psutil.STATUS_ZOMBIE)
        with patch('psutil.Process', return_value=proc):
            assert launch._is_our_server_process(99999) is False

    def test_no_such_process_returns_false(self):
        import launch
        import psutil
        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(pid=99999)):
            assert launch._is_our_server_process(99999) is False


# =========================================== kill_existing_server (mocked) ==

@pytest.mark.unit
class TestKillExistingServer:
    def test_kills_process_from_pid_file(self, tmp_pid_path):
        import launch
        import psutil

        launch._write_pid_file(pid=11111, port=8083)

        mock_proc = MagicMock()
        mock_proc.status.return_value = 'running'
        mock_proc.cmdline.return_value = ['python', 'launch.py', '--serve', '8083']

        with patch('psutil.Process', return_value=mock_proc):
            with patch.object(launch, '_find_server_on_port', return_value=None):
                launch.kill_existing_server(8083)

        mock_proc.terminate.assert_called_once()
        # PID file should be cleaned up
        assert not os.path.exists(tmp_pid_path)

    def test_cleans_up_stale_pid_file(self, tmp_pid_path):
        import launch
        import psutil

        launch._write_pid_file(pid=22222, port=8083)

        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(pid=22222)):
            with patch.object(launch, '_find_server_on_port', return_value=None):
                launch.kill_existing_server(8083)

        assert not os.path.exists(tmp_pid_path)

    def test_port_scan_fallback_when_no_pid_file(self, tmp_pid_path):
        import launch

        mock_proc = MagicMock()
        mock_proc.status.return_value = 'running'
        mock_proc.cmdline.return_value = ['python', 'launch.py', '--serve', '8083']

        with patch('psutil.Process', return_value=mock_proc):
            with patch.object(launch, '_find_server_on_port', return_value=33333):
                launch.kill_existing_server(8083)

        mock_proc.terminate.assert_called_once()

    def test_invalid_port_returns_early(self, tmp_pid_path):
        import launch
        with patch.object(launch, '_read_pid_file') as mock_read:
            launch.kill_existing_server(80)  # below 1024 — invalid
            mock_read.assert_not_called()


# ================================================== server_status (mocked) ==

@pytest.mark.unit
class TestServerStatus:
    def test_running_server_via_pid_file(self, tmp_pid_path):
        import launch
        import psutil

        launch._write_pid_file(pid=44444, port=8083)

        mock_proc = MagicMock()
        mock_proc.status.return_value = 'running'
        mock_proc.cmdline.return_value = ['python', 'launch.py', '--serve', '8083']
        mock_proc.create_time.return_value = datetime.now().timestamp() - 120

        with patch('psutil.Process', return_value=mock_proc):
            st = launch.server_status()

        assert st['running'] is True
        assert st['pid'] == 44444
        assert st['port'] == 8083
        assert st['uptime_seconds'] is not None
        assert st['uptime_seconds'] >= 0

    def test_stale_pid_file_reports_not_running(self, tmp_pid_path):
        import launch
        import psutil

        launch._write_pid_file(pid=55555, port=8083)

        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(pid=55555)):
            with patch.object(launch, '_find_server_on_port', return_value=None):
                st = launch.server_status()

        assert st['running'] is False
        # Stale file should be removed
        assert not os.path.exists(tmp_pid_path)

    def test_no_pid_file_not_running(self, tmp_pid_path):
        import launch
        with patch.object(launch, '_find_server_on_port', return_value=None):
            st = launch.server_status()
        assert st['running'] is False
        assert st['pid'] is None


# ===================================================== stop_server (mocked) ==

@pytest.mark.unit
class TestStopServer:
    def test_stops_tracked_server(self, tmp_pid_path):
        import launch

        launch._write_pid_file(pid=66666, port=8083)

        mock_proc = MagicMock()
        mock_proc.status.return_value = 'running'
        mock_proc.cmdline.return_value = ['python', 'launch.py', '--serve', '8083']

        with patch('psutil.Process', return_value=mock_proc):
            result = launch.stop_server()

        assert result is True
        mock_proc.terminate.assert_called_once()
        assert not os.path.exists(tmp_pid_path)

    def test_returns_false_when_no_server(self, tmp_pid_path):
        import launch
        with patch.object(launch, '_find_server_on_port', return_value=None):
            result = launch.stop_server()
        assert result is False
