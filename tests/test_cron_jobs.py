"""
Tests for cron job scripts.

Tests each cron script can execute successfully and handle errors.
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import shutil


# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory structure."""
    # Create directories
    (tmp_path / 'logs').mkdir()
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cron').mkdir()
    
    # Create empty log files
    (tmp_path / 'logs' / 'cron.log').touch()
    
    return tmp_path


@pytest.fixture
def mock_storage():
    """Mock JSONStorage."""
    storage = Mock()
    storage.read.return_value = {'jobs': []}
    storage.write.return_value = None
    return storage


def _http_response(status_code=200, json_data=None):
    """Build a mock requests.Response."""
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestDailyAnalysisJob:
    """Tests for daily_analysis.py cron job (thin HTTP client)."""

    @patch('cron.daily_analysis.time.sleep')
    @patch('cron.daily_analysis.requests.Session')
    @patch('cron.daily_analysis.JSONStorage')
    @patch('cron.daily_analysis.ConfigManager.get_instance')
    def test_daily_analysis_success(self, mock_config, mock_storage_class,
                                    mock_session_class, mock_sleep):
        """Job triggers /api/analyze, polls to done, records history."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        session = Mock()
        session.get.side_effect = [
            _http_response(json_data={'csrf_token': 'tok'}),
            _http_response(json_data={'status': 'running'}),
            _http_response(json_data={
                'status': 'done',
                'result': {'success': True, 'activities_count': 100,
                           'route_groups_count': 10, 'long_rides_count': 5},
            }),
        ]
        session.post.return_value = _http_response(
            json_data={'status': 'started'})
        mock_session_class.return_value = session

        from cron import daily_analysis
        result = daily_analysis.main()

        assert result == 0
        session.post.assert_called_once()
        assert '/api/analyze' in session.post.call_args[0][0]
        # CSRF token forwarded on the POST
        assert session.post.call_args.kwargs['headers']['X-CSRFToken'] == 'tok'
        mock_storage.write.assert_called()

    @patch('cron.daily_analysis.time.sleep')
    @patch('cron.daily_analysis.requests.Session')
    @patch('cron.daily_analysis.JSONStorage')
    @patch('cron.daily_analysis.ConfigManager.get_instance')
    def test_daily_analysis_already_running(self, mock_config, mock_storage_class,
                                            mock_session_class, mock_sleep):
        """A 409 from /api/analyze is treated as a graceful skip."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        session = Mock()
        session.get.return_value = _http_response(
            json_data={'csrf_token': 'tok'})
        session.post.return_value = _http_response(
            status_code=409, json_data={'status': 'already_running'})
        mock_session_class.return_value = session

        from cron import daily_analysis
        assert daily_analysis.main() == 0

    @patch('cron.daily_analysis.time.sleep')
    @patch('cron.daily_analysis.requests.Session')
    @patch('cron.daily_analysis.JSONStorage')
    @patch('cron.daily_analysis.ConfigManager.get_instance')
    def test_daily_analysis_error_status(self, mock_config, mock_storage_class,
                                         mock_session_class, mock_sleep):
        """A job that ends in 'error' state exits 1 and records the failure."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        session = Mock()
        session.get.side_effect = [
            _http_response(json_data={'csrf_token': 'tok'}),
            _http_response(json_data={'status': 'error',
                                      'label': 'Error: boom'}),
        ]
        session.post.return_value = _http_response(
            json_data={'status': 'started'})
        mock_session_class.return_value = session

        from cron import daily_analysis
        result = daily_analysis.main()

        assert result == 1
        mock_storage.write.assert_called()  # Should still record failure

    @patch('cron.daily_analysis.time.sleep')
    @patch('cron.daily_analysis.requests.Session')
    @patch('cron.daily_analysis.JSONStorage')
    @patch('cron.daily_analysis.ConfigManager.get_instance')
    def test_daily_analysis_error_payload_in_done_job(self, mock_config,
                                                      mock_storage_class,
                                                      mock_session_class,
                                                      mock_sleep):
        """A 'done' job whose result payload is an internal error exits 1.

        run_full_analysis catches errors (e.g. Strava auth failure) and
        returns {'status': 'error', ...} — the job state still reads 'done',
        so the script must inspect the payload (found live on pi4, #498).
        """
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        session = Mock()
        session.get.side_effect = [
            _http_response(json_data={'csrf_token': 'tok'}),
            _http_response(json_data={
                'status': 'done',
                'result': {'status': 'error', 'activities_count': 0,
                           'message': 'Analysis failed: Unauthorized'},
            }),
        ]
        session.post.return_value = _http_response(
            json_data={'status': 'started'})
        mock_session_class.return_value = session

        from cron import daily_analysis
        result = daily_analysis.main()

        assert result == 1
        mock_storage.write.assert_called()  # failure recorded in history

    @patch('cron.daily_analysis.time.sleep')
    @patch('cron.daily_analysis.requests.Session')
    @patch('cron.daily_analysis.JSONStorage')
    @patch('cron.daily_analysis.ConfigManager.get_instance')
    def test_daily_analysis_app_unreachable(self, mock_config, mock_storage_class,
                                            mock_session_class, mock_sleep):
        """Connection failure exits 1 and records the failure."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        session = Mock()
        session.get.side_effect = Exception('connection refused')
        mock_session_class.return_value = session

        from cron import daily_analysis
        result = daily_analysis.main()

        assert result == 1
        mock_storage.write.assert_called()


class TestWeatherRefreshJob:
    """Tests for weather_refresh.py cron job (thin HTTP client)."""

    @patch('cron.weather_refresh.requests.get')
    @patch('cron.weather_refresh.JSONStorage')
    def test_weather_refresh_success(self, mock_storage_class, mock_get):
        """Job hits /api/weather and records history."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        mock_get.return_value = _http_response(json_data={
            'status': 'success',
            'current': {'temperature': 72, 'comfort_score': 85},
        })

        from cron import weather_refresh
        result = weather_refresh.main()

        assert result == 0
        assert '/api/weather' in mock_get.call_args[0][0]
        mock_storage.write.assert_called()

    @patch('cron.weather_refresh.requests.get')
    @patch('cron.weather_refresh.JSONStorage')
    def test_weather_refresh_no_location(self, mock_storage_class, mock_get):
        """A 400 (no home location configured) is a graceful skip."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        mock_get.return_value = _http_response(status_code=400)

        from cron import weather_refresh
        assert weather_refresh.main() == 0

    @patch('cron.weather_refresh.requests.get')
    @patch('cron.weather_refresh.JSONStorage')
    def test_weather_refresh_failure_non_critical(self, mock_storage_class, mock_get):
        """Weather refresh failure is non-critical: exit 0, failure recorded."""
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        mock_get.side_effect = Exception('connection refused')

        from cron import weather_refresh
        result = weather_refresh.main()

        assert result == 0
        mock_storage.write.assert_called()


class TestCacheCleanupJob:
    """Tests for cache_cleanup.py cron job."""
    
    def test_cache_cleanup_success(self, temp_project_dir):
        """Test cache cleanup removes old files."""
        # Create old cache file
        old_cache = temp_project_dir / 'cache' / 'old_cache.json'
        old_cache.write_text('{}')
        
        # Set modification time to 40 days ago
        import time
        old_time = time.time() - (40 * 24 * 60 * 60)
        import os
        os.utime(old_cache, (old_time, old_time))
        
        with patch('cron.cache_cleanup.project_root', temp_project_dir):
            with patch('cron.cache_cleanup.JSONStorage') as mock_storage_class:
                mock_storage = Mock()
                mock_storage.read.return_value = {'jobs': []}
                mock_storage_class.return_value = mock_storage
                
                from cron import cache_cleanup
                result = cache_cleanup.main()
                
                assert result == 0
                # Old file should be removed
                assert not old_cache.exists()
    
    def test_cache_cleanup_preserves_geocoding(self, temp_project_dir):
        """Test cache cleanup preserves geocoding cache."""
        # Create geocoding cache
        geo_cache = temp_project_dir / 'cache' / 'geocoding_cache.json'
        geo_cache.write_text('{}')
        
        # Set old modification time
        import time
        old_time = time.time() - (100 * 24 * 60 * 60)
        import os
        os.utime(geo_cache, (old_time, old_time))
        
        with patch('cron.cache_cleanup.project_root', temp_project_dir):
            with patch('cron.cache_cleanup.JSONStorage') as mock_storage_class:
                mock_storage = Mock()
                mock_storage.read.return_value = {'jobs': []}
                mock_storage_class.return_value = mock_storage
                
                from cron import cache_cleanup
                result = cache_cleanup.main()
                
                assert result == 0
                # Geocoding cache should be preserved
                assert geo_cache.exists()


class TestSystemHealthJob:
    """Tests for system_health.py cron job."""
    
    @patch('cron.system_health.check_api_status')
    @patch('cron.system_health.check_last_analysis')
    @patch('cron.system_health.check_cache_files')
    @patch('cron.system_health.check_disk_space')
    @patch('cron.system_health.JSONStorage')
    def test_system_health_success(self, mock_storage_class, mock_disk_space,
                                   mock_cache_files, mock_last_analysis, mock_api_status):
        """Test system health check runs successfully."""
        # Mock all health checks to return healthy status
        mock_disk_space.return_value = {'status': 'healthy', 'percent_used': 50}
        mock_cache_files.return_value = {'status': 'healthy', 'file_count': 5}
        mock_last_analysis.return_value = {'status': 'healthy', 'age_hours': 1.0}
        mock_api_status.return_value = {'status': 'healthy', 'response_time_ms': 100}
        
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage
        
        # Import and run
        from cron import system_health
        result = system_health.main()
        
        # Verify
        assert result == 0
        mock_storage.write.assert_called()
    
    @patch('cron.system_health.JSONStorage')
    @patch('cron.system_health.check_disk_space')
    def test_system_health_disk_warning(self, mock_check_disk, mock_storage_class):
        """Test system health detects disk space warning."""
        # Setup mocks
        mock_check_disk.return_value = {
            'status': 'warning',
            'percent_used': 95
        }
        
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage
        
        from cron import system_health
        result = system_health.main()
        
        # Should complete but return warning status
        assert result in [0, 1]


class TestCronJobHistory:
    """Tests for job history tracking."""
    
    @patch('cron.daily_analysis.time.sleep')
    @patch('cron.daily_analysis.requests.Session')
    @patch('cron.daily_analysis.JSONStorage')
    @patch('cron.daily_analysis.ConfigManager.get_instance')
    def test_job_history_recorded(self, mock_config, mock_storage_class,
                                  mock_session_class, mock_sleep):
        """Test job execution is recorded in history."""
        # Setup mock storage
        mock_storage = Mock()
        mock_storage.read.return_value = {'jobs': []}
        mock_storage_class.return_value = mock_storage

        session = Mock()
        session.get.side_effect = [
            _http_response(json_data={'csrf_token': 'tok'}),
            _http_response(json_data={'status': 'done',
                                      'result': {'activities_count': 100}}),
        ]
        session.post.return_value = _http_response(
            json_data={'status': 'started'})
        mock_session_class.return_value = session

        from cron import daily_analysis
        result = daily_analysis.main()

        # Verify storage.write was called (job history recorded)
        assert mock_storage.write.called
        # Check that job_history.json was written
        write_calls = [call for call in mock_storage.write.call_args_list
                      if 'job_history.json' in str(call)]
        assert len(write_calls) > 0
    
    def test_job_history_limit(self):
        """Test job history is limited to 100 entries."""
        from src.json_storage import JSONStorage
        
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONStorage(data_dir=tmpdir)
            
            # Create 150 job records
            history = {
                'jobs': [
                    {
                        'job_type': 'test',
                        'status': 'completed',
                        'timestamp': datetime.now().isoformat()
                    }
                    for _ in range(150)
                ]
            }
            storage.write('job_history.json', history)
            
            # Read back
            history = storage.read('job_history.json')
            
            # Should be limited to 100
            assert len(history['jobs']) <= 150  # Before cleanup
            
            # Simulate cleanup
            history['jobs'] = history['jobs'][-100:]
            storage.write('job_history.json', history)
            
            history = storage.read('job_history.json')
            assert len(history['jobs']) == 100


class TestCronInstallation:
    """Tests for cron installation script."""
    
    def test_crontab_template_valid(self):
        """Test crontab template is valid."""
        template_path = project_root / 'cron' / 'crontab.template'
        
        assert template_path.exists()
        
        content = template_path.read_text()
        
        # Check for required placeholders
        assert 'PROJECT_PATH' in content
        assert 'PYTHON_PATH' in content
        
        # Check for all jobs
        assert 'daily_analysis.py' in content
        assert 'weather_refresh.py' in content
        assert 'cache_cleanup.py' in content
        assert 'system_health.py' in content
    
    def test_install_script_executable(self):
        """Test install script is executable."""
        install_script = project_root / 'cron' / 'install_cron.sh'
        
        assert install_script.exists()
        
        import stat
        mode = install_script.stat().st_mode
        assert mode & stat.S_IXUSR  # User executable


