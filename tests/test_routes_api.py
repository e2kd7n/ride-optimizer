"""
Unit tests for app/routes/api.py - Internal REST API endpoints.

Tests cover:
- Health check endpoint
- System status endpoint
- Data synchronization
- Background job management
- Cache management
- Analytics and metrics
- Error handlers
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from flask import Flask

from app.models import db, JobHistory, AnalysisSnapshot
from app.routes import api as api_module
from app.routes.api import _get_cache_statistics

api_bp = api_module.bp


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprint
    app.register_blueprint(api_bp)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Create a database session for testing."""
    with app.app_context():
        yield db.session


class TestHealth:
    """Tests for /api/health endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check returns system health status."""
        with patch('app.routes.api.HealthChecker') as mock_checker:
            mock_health = Mock()
            mock_health.to_dict.return_value = {
                'status': 'healthy',
                'checks': {'database': 'ok', 'scheduler': 'ok'}
            }
            mock_checker.return_value.check_all.return_value = mock_health
            
            response = client.get('/api/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert 'checks' in data
    
    def test_health_check_unhealthy(self, client):
        """Test health check when system is unhealthy."""
        with patch('app.routes.api.HealthChecker') as mock_checker:
            mock_health = Mock()
            mock_health.to_dict.return_value = {
                'status': 'unhealthy',
                'checks': {'database': 'error'}
            }
            mock_checker.return_value.check_all.return_value = mock_health
            
            response = client.get('/api/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'unhealthy'


class TestStatus:
    """Tests for /api/status endpoint."""
    
    def test_status_with_data(self, client, db_session):
        """Test status endpoint with existing data."""
        # Create test snapshot
        snapshot = AnalysisSnapshot(
            analysis_date=datetime.now(timezone.utc),
            status='completed',
            activities_count=100,
            route_groups_count=25,
            long_rides_count=10
        )
        db_session.add(snapshot)
        
        # Create test jobs
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        job1 = JobHistory(
            job_id='test_job_1',
            job_name='Test Job 1',
            job_type='sync_strava',
            status='running',
            started_at=cutoff + timedelta(hours=1)
        )
        job2 = JobHistory(
            job_id='test_job_2',
            job_name='Test Job 2',
            job_type='sync_weather',
            status='pending',
            queued_at=cutoff + timedelta(hours=2)
        )
        job3 = JobHistory(
            job_id='test_job_3',
            job_name='Test Job 3',
            job_type='sync_all',
            status='failed',
            started_at=cutoff + timedelta(hours=3)
        )
        db_session.add_all([job1, job2, job3])
        db_session.commit()
        
        with patch('app.routes.api._get_cache_statistics') as mock_cache, \
             patch('app.routes.api.get_scheduler_status') as mock_scheduler:
            mock_cache.return_value = {'geocoding': {'entries': 50}}
            mock_scheduler.return_value = {'running': True, 'jobs_count': 3}
            
            response = client.get('/api/status')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'timestamp' in data
            assert data['data_freshness']['activities_count'] == 100
            assert data['background_jobs']['active'] == 1
            assert data['background_jobs']['queued'] == 1
            assert data['background_jobs']['failed'] == 1
            assert data['scheduler']['running'] is True
    
    def test_status_no_data(self, client):
        """Test status endpoint with no existing data."""
        with patch('app.routes.api._get_cache_statistics') as mock_cache, \
             patch('app.routes.api.get_scheduler_status') as mock_scheduler:
            mock_cache.return_value = {}
            mock_scheduler.return_value = {'running': False, 'jobs_count': 0}
            
            response = client.get('/api/status')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['data_freshness']['activities'] is None
            assert data['background_jobs']['active'] == 0


class TestGetCacheStatistics:
    """Tests for _get_cache_statistics helper function."""
    
    def test_cache_stats_no_directory(self):
        """Test cache stats when cache directory doesn't exist."""
        with patch('app.routes.api.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            stats = _get_cache_statistics()
            
            assert stats == {}
    
    def test_cache_stats_with_files(self):
        """Test cache stats with existing cache files."""
        mock_cache_file = Mock()
        mock_cache_file.stem = 'geocoding_cache'
        mock_cache_file.stat.return_value.st_size = 1024 * 1024  # 1 MB
        mock_cache_file.stat.return_value.st_mtime = datetime.now(timezone.utc).timestamp()
        
        with patch('app.routes.api.Path') as mock_path, \
             patch('builtins.open', mock_open(read_data='{"key1": "value1", "key2": "value2"}')):
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = [mock_cache_file]
            
            stats = _get_cache_statistics()
            
            assert 'geocoding' in stats
            assert stats['geocoding']['entries'] == 2
            assert stats['geocoding']['size_mb'] == 1.0
    
    def test_cache_stats_with_error(self, app):
        """Test cache stats handles file read errors gracefully."""
        mock_cache_file = Mock()
        mock_cache_file.stem = 'weather_cache'
        mock_cache_file.stat.side_effect = Exception("File error")
        
        with app.app_context():
            with patch('app.routes.api.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.glob.return_value = [mock_cache_file]
                
                stats = _get_cache_statistics()
                
                assert stats == {}


class TestSync:
    """Tests for /api/sync endpoint."""
    
    def test_sync_all_sources(self, client, db_session):
        """Test triggering sync for all sources."""
        with patch('app.routes.api.scheduler') as mock_scheduler:
            mock_scheduler.running = True
            
            response = client.post('/api/sync', json={
                'source': 'all',
                'force': False
            })
            
            assert response.status_code == 202
            data = response.get_json()
            assert data['status'] == 'queued'
            assert data['source'] == 'all'
            assert 'job_id' in data
            
            # Verify job was created
            job = JobHistory.query.first()
            assert job is not None
            assert job.job_type == 'sync_all'
            assert job.status == 'pending'
    
    def test_sync_specific_source(self, client, db_session):
        """Test triggering sync for specific source."""
        with patch('app.routes.api.scheduler') as mock_scheduler:
            mock_scheduler.running = True
            
            response = client.post('/api/sync', json={
                'source': 'strava',
                'force': True
            })
            
            assert response.status_code == 202
            data = response.get_json()
            assert data['source'] == 'strava'
            
            job = JobHistory.query.first()
            assert 'force=True' in job.description
    
    def test_sync_no_body(self, client, db_session):
        """Test sync with no request body uses defaults."""
        with patch('app.routes.api.scheduler') as mock_scheduler:
            mock_scheduler.running = False
            
            response = client.post('/api/sync')
            
            assert response.status_code == 202
            data = response.get_json()
            assert data['source'] == 'all'


class TestJobs:
    """Tests for /api/jobs endpoint."""
    
    def test_list_all_jobs(self, client, db_session):
        """Test listing all jobs."""
        # Create test jobs
        for i in range(3):
            job = JobHistory(
                job_id=f'test_job_{i}',
                job_name=f'Test Job {i}',
                job_type=f'test_type_{i}',
                status='completed'
            )
            db_session.add(job)
        db_session.commit()
        
        response = client.get('/api/jobs')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 3
        assert len(data['jobs']) == 3
        assert data['filter'] == 'all'
    
    def test_list_jobs_filtered(self, client, db_session):
        """Test listing jobs with status filter."""
        job1 = JobHistory(job_id='job1', job_name='Job 1', job_type='type1', status='completed')
        job2 = JobHistory(job_id='job2', job_name='Job 2', job_type='type2', status='failed')
        job3 = JobHistory(job_id='job3', job_name='Job 3', job_type='type3', status='completed')
        db_session.add_all([job1, job2, job3])
        db_session.commit()
        
        response = client.get('/api/jobs?status=completed')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 2
        assert data['filter'] == 'completed'
    
    def test_list_jobs_with_limit(self, client, db_session):
        """Test listing jobs with limit."""
        for i in range(10):
            job = JobHistory(
                job_id=f'job_{i}',
                job_name=f'Job {i}',
                job_type=f'type_{i}',
                status='completed'
            )
            db_session.add(job)
        db_session.commit()
        
        response = client.get('/api/jobs?limit=5')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['jobs']) == 5
        assert data['limit'] == 5


class TestJobStatus:
    """Tests for /api/jobs/<id> endpoint."""
    
    def test_get_job_status(self, client, db_session):
        """Test getting status of specific job."""
        job = JobHistory(
            job_id='test_job_123',
            job_name='Test Job',
            job_type='test_type',
            status='completed',
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=10.5
        )
        db_session.add(job)
        db_session.commit()
        
        response = client.get(f'/api/jobs/{job.id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == job.id
        assert data['job_type'] == 'test_type'
        assert data['status'] == 'completed'
        assert data['duration_seconds'] == 10.5
    
    def test_get_job_not_found(self, client):
        """Test getting non-existent job returns 404."""
        response = client.get('/api/jobs/99999')
        
        assert response.status_code == 404


class TestCancelJob:
    """Tests for /api/jobs/<id>/cancel endpoint."""
    
    def test_cancel_running_job(self, client, db_session):
        """Test cancelling a running job."""
        job = JobHistory(
            job_id='test_job_456',
            job_name='Test Job',
            job_type='test_type',
            status='running',
            started_at=datetime.now(timezone.utc)
        )
        db_session.add(job)
        db_session.commit()
        
        with patch('app.routes.api.scheduler') as mock_scheduler:
            mock_scheduler.running = True
            
            response = client.post(f'/api/jobs/{job.id}/cancel')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'cancelled'
            assert data['job_id'] == job.id
            
            # Verify job was updated
            db_session.refresh(job)
            assert job.status == 'cancelled'
            assert job.completed_at is not None
    
    def test_cancel_already_completed_job(self, client, db_session):
        """Test cancelling already completed job returns error."""
        job = JobHistory(
            job_id='test_job_789',
            job_name='Test Job',
            job_type='test_type',
            status='completed',
            completed_at=datetime.now(timezone.utc)
        )
        db_session.add(job)
        db_session.commit()
        
        response = client.post(f'/api/jobs/{job.id}/cancel')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert data['status'] == 'completed'
    
    def test_cancel_job_not_found(self, client):
        """Test cancelling non-existent job returns 404."""
        response = client.post('/api/jobs/99999/cancel')
        
        assert response.status_code == 404


class TestCacheStats:
    """Tests for /api/cache/stats endpoint."""
    
    def test_cache_stats(self, client):
        """Test getting cache statistics."""
        with patch('app.routes.api._get_cache_statistics') as mock_stats:
            mock_stats.return_value = {
                'geocoding': {'entries': 100, 'size_mb': 2.5},
                'weather': {'entries': 50, 'size_mb': 1.0}
            }
            
            response = client.get('/api/cache/stats')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'timestamp' in data
            assert data['total_size_mb'] == 3.5
            assert data['total_entries'] == 150
            assert 'geocoding' in data['caches']


class TestClearCache:
    """Tests for /api/cache/clear endpoint."""
    
    def test_clear_cache_without_confirm(self, client):
        """Test clearing cache without confirmation returns error."""
        response = client.post('/api/cache/clear', json={
            'cache_type': 'all',
            'confirm': False
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Confirmation required' in data['error']
    
    def test_clear_specific_cache(self, client):
        """Test clearing specific cache type."""
        mock_file = Mock()
        mock_file.stat.return_value.st_size = 1024 * 1024
        mock_file.name = 'geocoding_cache.json'
        
        with patch('app.routes.api.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = [mock_file]
            
            response = client.post('/api/cache/clear', json={
                'cache_type': 'geocoding',
                'confirm': True
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'cleared'
            assert data['cache_type'] == 'geocoding'
            assert data['files_removed'] == 1
            assert data['size_freed_mb'] == 1.0
            mock_file.unlink.assert_called_once()
    
    def test_clear_all_caches(self, client):
        """Test clearing all cache types."""
        mock_files = [Mock() for _ in range(3)]
        for i, mock_file in enumerate(mock_files):
            mock_file.stat.return_value.st_size = 1024 * 1024
            mock_file.name = f'cache_{i}.json'
        
        with patch('app.routes.api.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = mock_files
            
            response = client.post('/api/cache/clear', json={
                'cache_type': 'all',
                'confirm': True
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['files_removed'] == 3
            assert data['size_freed_mb'] == 3.0
    
    def test_clear_cache_directory_not_found(self, client):
        """Test clearing cache when directory doesn't exist."""
        with patch('app.routes.api.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            response = client.post('/api/cache/clear', json={
                'cache_type': 'all',
                'confirm': True
            })
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data


class TestAnalyticsSummary:
    """Tests for /api/analytics/summary endpoint."""
    
    def test_analytics_with_data(self, client, db_session):
        """Test analytics summary with existing data."""
        # Create snapshot with route groups
        snapshot = AnalysisSnapshot(
            analysis_date=datetime.now(timezone.utc),
            status='completed',
            activities_count=200,
            route_groups_count=50,
            long_rides_count=15
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Mock route groups
        mock_route_groups = [
            Mock(id=1, name='Route 1', uses_count=50),
            Mock(id=2, name='Route 2', uses_count=30),
            Mock(id=3, name='Route 3', uses_count=20)
        ]
        snapshot.route_groups = mock_route_groups
        
        response = client.get('/api/analytics/summary')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['activities']['total'] == 200
        assert data['routes']['total'] == 50
        assert data['long_rides']['total'] == 15
        assert len(data['routes']['most_used']) == 3
        assert data['routes']['most_used'][0]['uses_count'] == 50
    
    def test_analytics_no_data(self, client):
        """Test analytics summary with no data returns 404."""
        response = client.get('/api/analytics/summary')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


class TestMetrics:
    """Tests for /api/metrics endpoint."""
    
    def test_metrics_prometheus_format(self, client, db_session):
        """Test metrics endpoint returns Prometheus format."""
        # Create test data
        snapshot = AnalysisSnapshot(
            analysis_date=datetime.now(timezone.utc),
            activities_count=100,
            route_groups_count=25,
            long_rides_count=10
        )
        db_session.add(snapshot)
        
        for i in range(5):
            job = JobHistory(
                job_type='test',
                status='failed' if i < 2 else 'completed'
            )
            db_session.add(job)
        db_session.commit()
        
        with patch('app.routes.api._get_cache_statistics') as mock_cache, \
             patch('app.routes.api.scheduler') as mock_scheduler:
            mock_cache.return_value = {
                'geocoding': {'size_mb': 2.5},
                'weather': {'size_mb': 1.5}
            }
            mock_scheduler.running = True
            
            response = client.get('/api/metrics')
            
            assert response.status_code == 200
            assert response.content_type == 'text/plain; charset=utf-8'
            
            text = response.get_data(as_text=True)
            assert 'ride_optimizer_activities_total 100' in text
            assert 'ride_optimizer_routes_total 25' in text
            assert 'ride_optimizer_long_rides_total 10' in text
            assert 'ride_optimizer_jobs_total 5' in text
            assert 'ride_optimizer_jobs_failed_total 2' in text
            assert 'ride_optimizer_cache_size_mb 4.0' in text
            assert 'ride_optimizer_scheduler_running 1' in text
    
    def test_metrics_no_data(self, client):
        """Test metrics with no data returns zeros."""
        with patch('app.routes.api._get_cache_statistics') as mock_cache, \
             patch('app.routes.api.scheduler') as mock_scheduler:
            mock_cache.return_value = {}
            mock_scheduler.running = False
            
            response = client.get('/api/metrics')
            
            assert response.status_code == 200
            text = response.get_data(as_text=True)
            assert 'ride_optimizer_activities_total 0' in text
            assert 'ride_optimizer_scheduler_running 0' in text


class TestErrorHandlers:
    """Tests for API error handlers."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler returns JSON."""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Not Found'
        assert 'message' in data
    
    def test_500_error_handler(self, client):
        """Test 500 error handler returns JSON."""
        with patch('app.routes.api.AnalysisSnapshot.query') as mock_query:
            mock_query.order_by.side_effect = Exception("Database error")
            
            response = client.get('/api/status')
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['error'] == 'Internal Server Error'
            assert 'message' in data

# Made with Bob
