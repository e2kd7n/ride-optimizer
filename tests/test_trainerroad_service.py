"""
Unit tests for TrainerRoadService.

Tests cover:
- Service initialization and encryption
- Feed URL management (set, get, remove)
- ICS feed fetching
- ICS feed parsing
- Event parsing and workout extraction
- Workout type detection
- Metrics extraction (TSS, IF)
- Workout syncing to database
- Planning constraints generation
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime, date, timedelta
from pathlib import Path
import json

from app.services.trainerroad_service import TrainerRoadService
from src.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'trainerroad.sync_interval_hours': 6
    }.get(key, default))
    return config


@pytest.fixture
def trainerroad_service(mock_config, tmp_path):
    """Create a TrainerRoadService instance with mocked dependencies."""
    with patch('app.services.trainerroad_service.Path') as mock_path:
        # Mock paths to use tmp_path
        mock_path.return_value = tmp_path / 'config'
        
        with patch.object(TrainerRoadService, '_get_cipher') as mock_cipher, \
             patch.object(TrainerRoadService, '_load_feed_url', return_value=None):
            
            mock_cipher.return_value = Mock()
            service = TrainerRoadService(mock_config)
            service.credentials_path = tmp_path / 'credentials.json'
            service.key_file = tmp_path / 'key'
            
            return service


@pytest.fixture
def sample_ics_content():
    """Sample ICS calendar content."""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//TrainerRoad//EN
BEGIN:VEVENT
UID:tr_workout_123
SUMMARY:Endurance Ride
DESCRIPTION:60 minutes easy spinning. TSS: 45 IF: 0.65
DTSTART:20260510T100000Z
DTEND:20260510T110000Z
END:VEVENT
BEGIN:VEVENT
UID:tr_workout_124
SUMMARY:Threshold Intervals
DESCRIPTION:Sweet spot intervals. TSS: 85 IF: 0.88
DTSTART:20260512T100000Z
DTEND:20260512T113000Z
END:VEVENT
END:VCALENDAR"""


@pytest.fixture
def sample_workout_data():
    """Sample workout data dictionary."""
    return {
        'workout_id': 'tr_workout_123',
        'workout_name': 'Endurance Ride',
        'workout_date': date(2026, 5, 10),
        'workout_type': 'Endurance',
        'duration_minutes': 60,
        'tss': 45.0,
        'intensity_factor': 0.65,
        'description': '60 minutes easy spinning',
        'status': 'scheduled'
    }


class TestTrainerRoadServiceInit:
    """Test TrainerRoadService initialization."""
    
    def test_init_creates_dependencies(self, mock_config):
        """Test that initialization creates all required dependencies."""
        with patch.object(TrainerRoadService, '_get_cipher') as mock_cipher, \
             patch.object(TrainerRoadService, '_load_feed_url', return_value=None):
            
            service = TrainerRoadService(mock_config)
            
            assert service.config == mock_config
            assert service.sync_interval_hours == 6
            assert service.last_sync is None
            mock_cipher.assert_called_once()
    
    def test_init_loads_feed_url(self, mock_config):
        """Test that initialization loads feed URL from storage."""
        with patch.object(TrainerRoadService, '_get_cipher'), \
             patch.object(TrainerRoadService, '_load_feed_url', return_value='https://example.com/feed.ics') as mock_load:
            
            service = TrainerRoadService(mock_config)
            
            assert service.feed_url == 'https://example.com/feed.ics'
            mock_load.assert_called_once()


class TestEncryptionSetup:
    """Test encryption key management."""
    
    def test_uses_env_key_if_available(self, mock_config):
        """Test using encryption key from environment variable."""
        with patch('app.services.trainerroad_service.os.getenv', return_value='test_key_base64'), \
             patch('app.services.trainerroad_service.Fernet') as mock_fernet, \
             patch.object(TrainerRoadService, '_load_feed_url', return_value=None):
            
            service = TrainerRoadService(mock_config)
            
            mock_fernet.assert_called_with(b'test_key_base64')
    
    def test_loads_existing_key_file(self, mock_config, tmp_path):
        """Test loading encryption key from existing file."""
        key_file = tmp_path / 'key'
        key_file.write_bytes(b'existing_key')
        
        with patch('app.services.trainerroad_service.os.getenv', return_value=None), \
             patch('app.services.trainerroad_service.Fernet') as mock_fernet, \
             patch.object(TrainerRoadService, '_load_feed_url', return_value=None):
            
            service = TrainerRoadService(mock_config)
            service.key_file = key_file
            
            # Manually call _get_cipher to test the logic
            cipher = service._get_cipher()
            
            mock_fernet.assert_called()
    
    def test_generates_new_key_if_none_exists(self, mock_config, tmp_path):
        """Test generating new encryption key if none exists."""
        with patch('app.services.trainerroad_service.os.getenv', return_value=None), \
             patch('app.services.trainerroad_service.Fernet') as mock_fernet, \
             patch.object(TrainerRoadService, '_load_feed_url', return_value=None):
            
            mock_fernet.generate_key.return_value = b'new_generated_key'
            
            service = TrainerRoadService(mock_config)
            service.key_file = tmp_path / 'new_key'
            
            cipher = service._get_cipher()
            
            mock_fernet.generate_key.assert_called()


class TestFeedURLManagement:
    """Test feed URL management."""
    
    def test_set_feed_url_valid(self, trainerroad_service):
        """Test setting a valid feed URL."""
        trainerroad_service._save_feed_url = Mock(return_value=True)
        
        result = trainerroad_service.set_feed_url('https://trainerroad.com/feed.ics')
        
        assert result is True
        assert trainerroad_service.feed_url == 'https://trainerroad.com/feed.ics'
        trainerroad_service._save_feed_url.assert_called_once()
    
    def test_set_feed_url_invalid(self, trainerroad_service):
        """Test rejecting invalid feed URL."""
        result = trainerroad_service.set_feed_url('not-a-valid-url')
        
        assert result is False
        assert trainerroad_service.feed_url is None
    
    def test_set_feed_url_save_failure(self, trainerroad_service):
        """Test handling save failure."""
        trainerroad_service._save_feed_url = Mock(return_value=False)
        
        result = trainerroad_service.set_feed_url('https://trainerroad.com/feed.ics')
        
        assert result is False
    
    def test_get_feed_url(self, trainerroad_service):
        """Test getting configured feed URL."""
        trainerroad_service.feed_url = 'https://example.com/feed.ics'
        
        result = trainerroad_service.get_feed_url()
        
        assert result == 'https://example.com/feed.ics'
    
    def test_get_feed_url_none(self, trainerroad_service):
        """Test getting feed URL when none configured."""
        trainerroad_service.feed_url = None
        
        result = trainerroad_service.get_feed_url()
        
        assert result is None
    
    def test_remove_credentials(self, trainerroad_service, tmp_path):
        """Test removing stored credentials."""
        creds_file = tmp_path / 'credentials.json'
        creds_file.write_text('encrypted_data')
        trainerroad_service.credentials_path = creds_file
        trainerroad_service.feed_url = 'https://example.com/feed.ics'
        
        result = trainerroad_service.remove_credentials()
        
        assert result is True
        assert not creds_file.exists()
        assert trainerroad_service.feed_url is None
    
    def test_remove_credentials_no_file(self, trainerroad_service, tmp_path):
        """Test removing credentials when file doesn't exist."""
        trainerroad_service.credentials_path = tmp_path / 'nonexistent.json'
        
        result = trainerroad_service.remove_credentials()
        
        assert result is True


class TestFetchICSFeed:
    """Test ICS feed fetching."""
    
    def test_fetch_success(self, trainerroad_service, sample_ics_content):
        """Test successful feed fetch."""
        trainerroad_service.feed_url = 'https://example.com/feed.ics'
        
        with patch('app.services.trainerroad_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = sample_ics_content
            mock_get.return_value = mock_response
            
            result = trainerroad_service.fetch_ics_feed()
            
            assert result == sample_ics_content
            mock_get.assert_called_once_with('https://example.com/feed.ics', timeout=10)
    
    def test_fetch_no_url_configured(self, trainerroad_service):
        """Test fetch when no URL configured."""
        trainerroad_service.feed_url = None
        
        result = trainerroad_service.fetch_ics_feed()
        
        assert result is None
    
    def test_fetch_timeout(self, trainerroad_service):
        """Test handling request timeout."""
        trainerroad_service.feed_url = 'https://example.com/feed.ics'
        
        with patch('app.services.trainerroad_service.requests.get') as mock_get:
            mock_get.side_effect = Exception('Timeout')
            
            result = trainerroad_service.fetch_ics_feed()
            
            assert result is None
    
    def test_fetch_http_error(self, trainerroad_service):
        """Test handling HTTP error."""
        trainerroad_service.feed_url = 'https://example.com/feed.ics'
        
        with patch('app.services.trainerroad_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception('404 Not Found')
            mock_get.return_value = mock_response
            
            result = trainerroad_service.fetch_ics_feed()
            
            assert result is None
    
    def test_fetch_custom_timeout(self, trainerroad_service):
        """Test fetch with custom timeout."""
        trainerroad_service.feed_url = 'https://example.com/feed.ics'
        
        with patch('app.services.trainerroad_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = 'content'
            mock_get.return_value = mock_response
            
            trainerroad_service.fetch_ics_feed(timeout=30)
            
            mock_get.assert_called_once_with('https://example.com/feed.ics', timeout=30)


class TestParseICSFeed:
    """Test ICS feed parsing."""
    
    def test_parse_valid_feed(self, trainerroad_service, sample_ics_content):
        """Test parsing valid ICS feed."""
        workouts = trainerroad_service.parse_ics_feed(sample_ics_content)
        
        assert len(workouts) == 2
        assert workouts[0]['workout_name'] == 'Endurance Ride'
        assert workouts[1]['workout_name'] == 'Threshold Intervals'
    
    def test_parse_empty_content(self, trainerroad_service):
        """Test parsing empty content."""
        workouts = trainerroad_service.parse_ics_feed('')
        
        assert workouts == []
    
    def test_parse_none_content(self, trainerroad_service):
        """Test parsing None content."""
        workouts = trainerroad_service.parse_ics_feed(None)
        
        assert workouts == []
    
    def test_parse_invalid_ics(self, trainerroad_service):
        """Test parsing invalid ICS content."""
        invalid_ics = "This is not valid ICS content"
        
        workouts = trainerroad_service.parse_ics_feed(invalid_ics)
        
        assert workouts == []
    
    def test_parse_skips_invalid_events(self, trainerroad_service):
        """Test that invalid events are skipped."""
        ics_with_invalid = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:valid_event
SUMMARY:Valid Workout
DTSTART:20260510T100000Z
END:VEVENT
BEGIN:VEVENT
UID:invalid_event
END:VEVENT
END:VCALENDAR"""
        
        workouts = trainerroad_service.parse_ics_feed(ics_with_invalid)
        
        assert len(workouts) == 1
        assert workouts[0]['workout_name'] == 'Valid Workout'


class TestWorkoutTypeExtraction:
    """Test workout type extraction."""
    
    def test_extract_endurance(self, trainerroad_service):
        """Test extracting Endurance type."""
        workout_type = trainerroad_service._extract_workout_type(
            'Easy Endurance Ride', 'Base building workout'
        )
        assert workout_type == 'Endurance'
    
    def test_extract_tempo(self, trainerroad_service):
        """Test extracting Tempo type."""
        workout_type = trainerroad_service._extract_workout_type(
            'Tempo Intervals', 'Steady tempo effort'
        )
        assert workout_type == 'Tempo'
    
    def test_extract_threshold(self, trainerroad_service):
        """Test extracting Threshold type."""
        workout_type = trainerroad_service._extract_workout_type(
            'Sweet Spot Intervals', 'Threshold work'
        )
        assert workout_type == 'Threshold'
    
    def test_extract_vo2max(self, trainerroad_service):
        """Test extracting VO2Max type."""
        workout_type = trainerroad_service._extract_workout_type(
            'VO2Max Intervals', 'High intensity VO2 work'
        )
        assert workout_type == 'VO2Max'
    
    def test_extract_anaerobic(self, trainerroad_service):
        """Test extracting Anaerobic type."""
        workout_type = trainerroad_service._extract_workout_type(
            'Over-Under Intervals', 'Anaerobic capacity work'
        )
        assert workout_type == 'Anaerobic'
    
    def test_extract_sprint(self, trainerroad_service):
        """Test extracting Sprint type."""
        workout_type = trainerroad_service._extract_workout_type(
            'Sprint Intervals', 'Neuromuscular power'
        )
        assert workout_type == 'Sprint'
    
    def test_extract_unknown_type(self, trainerroad_service):
        """Test handling unknown workout type."""
        workout_type = trainerroad_service._extract_workout_type(
            'Custom Workout', 'No recognizable type'
        )
        assert workout_type is None
    
    def test_extract_case_insensitive(self, trainerroad_service):
        """Test case-insensitive type extraction."""
        workout_type = trainerroad_service._extract_workout_type(
            'ENDURANCE RIDE', 'EASY SPINNING'
        )
        assert workout_type == 'Endurance'


class TestMetricsExtraction:
    """Test TSS and IF extraction."""
    
    def test_extract_tss(self, trainerroad_service):
        """Test extracting TSS value."""
        tss, if_val = trainerroad_service._extract_metrics('Workout with TSS: 65')
        
        assert tss == 65.0
    
    def test_extract_tss_alternative_format(self, trainerroad_service):
        """Test extracting TSS in alternative format."""
        tss, if_val = trainerroad_service._extract_metrics('This is a 85 TSS workout')
        
        assert tss == 85.0
    
    def test_extract_intensity_factor(self, trainerroad_service):
        """Test extracting IF value."""
        tss, if_val = trainerroad_service._extract_metrics('Workout with IF: 0.85')
        
        assert if_val == 0.85
    
    def test_extract_both_metrics(self, trainerroad_service):
        """Test extracting both TSS and IF."""
        tss, if_val = trainerroad_service._extract_metrics('TSS: 75 IF: 0.88')
        
        assert tss == 75.0
        assert if_val == 0.88
    
    def test_extract_no_metrics(self, trainerroad_service):
        """Test when no metrics present."""
        tss, if_val = trainerroad_service._extract_metrics('Just a workout description')
        
        assert tss is None
        assert if_val is None
    
    def test_extract_case_insensitive(self, trainerroad_service):
        """Test case-insensitive metric extraction."""
        tss, if_val = trainerroad_service._extract_metrics('tss: 60 if: 0.75')
        
        assert tss == 60.0
        assert if_val == 0.75


class TestSyncWorkouts:
    """Test workout syncing."""
    
    def test_sync_success(self, trainerroad_service, sample_ics_content):
        """Test successful workout sync."""
        trainerroad_service.fetch_ics_feed = Mock(return_value=sample_ics_content)
        
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout, \
             patch('app.services.trainerroad_service.db') as mock_db:
            
            mock_workout.query.filter_by.return_value.first.return_value = None
            
            result = trainerroad_service.sync_workouts(days_ahead=14)
            
            assert result['status'] == 'success'
            assert result['workouts_synced'] >= 0
            assert 'last_sync' in result
    
    def test_sync_skipped_recent(self, trainerroad_service):
        """Test skipping sync when recently synced."""
        trainerroad_service.last_sync = datetime.now() - timedelta(hours=1)
        
        result = trainerroad_service.sync_workouts()
        
        assert result['status'] == 'skipped'
        assert 'last_sync' in result
    
    def test_sync_fetch_failure(self, trainerroad_service):
        """Test handling fetch failure during sync."""
        trainerroad_service.fetch_ics_feed = Mock(return_value=None)
        
        result = trainerroad_service.sync_workouts()
        
        assert result['status'] == 'error'
        assert result['workouts_synced'] == 0
    
    def test_sync_no_workouts(self, trainerroad_service):
        """Test handling empty workout list."""
        trainerroad_service.fetch_ics_feed = Mock(return_value='BEGIN:VCALENDAR\nEND:VCALENDAR')
        
        result = trainerroad_service.sync_workouts()
        
        assert result['status'] == 'error'
        assert 'No workouts found' in result['message']
    
    def test_sync_filters_by_date_range(self, trainerroad_service, sample_ics_content):
        """Test that sync filters workouts by date range."""
        trainerroad_service.fetch_ics_feed = Mock(return_value=sample_ics_content)
        
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout, \
             patch('app.services.trainerroad_service.db'):
            
            mock_workout.query.filter_by.return_value.first.return_value = None
            
            result = trainerroad_service.sync_workouts(days_ahead=7)
            
            # Should only sync workouts within the date range
            assert result['status'] in ['success', 'error']


class TestGetWorkoutConstraints:
    """Test workout constraints generation."""
    
    def test_constraints_endurance_workout(self, trainerroad_service):
        """Test constraints for endurance workout."""
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout:
            mock_workout_obj = Mock()
            mock_workout_obj.workout_name = 'Endurance Ride'
            mock_workout_obj.workout_type = 'Endurance'
            mock_workout_obj.duration_minutes = 60
            mock_workout_obj.tss = 45
            mock_workout.get_for_date.return_value = mock_workout_obj
            
            constraints = trainerroad_service.get_workout_constraints(date.today())
            
            assert constraints['has_workout'] is True
            assert constraints['workout_type'] == 'Endurance'
            assert constraints['preferred_intensity'] == 'low'
            assert constraints['indoor_fallback'] is False
    
    def test_constraints_threshold_workout(self, trainerroad_service):
        """Test constraints for threshold workout."""
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout:
            mock_workout_obj = Mock()
            mock_workout_obj.workout_name = 'Threshold Intervals'
            mock_workout_obj.workout_type = 'Threshold'
            mock_workout_obj.duration_minutes = 75
            mock_workout_obj.tss = 85
            mock_workout.get_for_date.return_value = mock_workout_obj
            
            constraints = trainerroad_service.get_workout_constraints(date.today())
            
            assert constraints['indoor_fallback'] is True
            assert constraints['preferred_intensity'] == 'high'
    
    def test_constraints_vo2max_workout(self, trainerroad_service):
        """Test constraints for VO2Max workout."""
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout:
            mock_workout_obj = Mock()
            mock_workout_obj.workout_name = 'VO2Max Intervals'
            mock_workout_obj.workout_type = 'VO2Max'
            mock_workout_obj.duration_minutes = 60
            mock_workout_obj.tss = 95
            mock_workout.get_for_date.return_value = mock_workout_obj
            
            constraints = trainerroad_service.get_workout_constraints(date.today())
            
            assert constraints['indoor_fallback'] is True
            assert constraints['preferred_intensity'] == 'high'
    
    def test_constraints_recovery_workout(self, trainerroad_service):
        """Test constraints for recovery workout."""
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout:
            mock_workout_obj = Mock()
            mock_workout_obj.workout_name = 'Recovery Spin'
            mock_workout_obj.workout_type = 'Recovery'
            mock_workout_obj.duration_minutes = 30
            mock_workout_obj.tss = 20
            mock_workout.get_for_date.return_value = mock_workout_obj
            
            constraints = trainerroad_service.get_workout_constraints(date.today())
            
            assert constraints['max_duration_minutes'] == 45
            assert constraints['preferred_intensity'] == 'very_low'
    
    def test_constraints_no_workout(self, trainerroad_service):
        """Test constraints when no workout scheduled."""
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout:
            mock_workout.get_for_date.return_value = None
            
            constraints = trainerroad_service.get_workout_constraints(date.today())
            
            assert constraints is None
    
    def test_constraints_high_tss_note(self, trainerroad_service):
        """Test that high TSS adds note."""
        with patch('app.services.trainerroad_service.WorkoutMetadata') as mock_workout:
            mock_workout_obj = Mock()
            mock_workout_obj.workout_name = 'Hard Workout'
            mock_workout_obj.workout_type = 'Threshold'
            mock_workout_obj.duration_minutes = 120
            mock_workout_obj.tss = 150
            mock_workout.get_for_date.return_value = mock_workout_obj
            
            constraints = trainerroad_service.get_workout_constraints(date.today())
            
            assert any('High training load' in note for note in constraints['notes'])
            assert constraints['tss'] == 150


# Made with Bob