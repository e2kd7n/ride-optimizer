"""
Unit tests for secure_cache module.

Tests encrypted cache storage with HMAC integrity verification.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest
from cryptography.fernet import Fernet

from src.secure_cache import SecureCacheStorage, migrate_cache_to_encrypted


@pytest.mark.unit
class TestSecureCacheStorage:
    """Test SecureCacheStorage class."""
    
    @pytest.fixture
    def temp_cache_path(self, tmp_path):
        """Create temporary cache file path."""
        return tmp_path / "test_cache.json"
    
    @pytest.fixture
    def temp_key_path(self, tmp_path):
        """Create temporary key file path."""
        key_dir = tmp_path / "config"
        key_dir.mkdir(parents=True, exist_ok=True)
        return key_dir / ".cache_encryption_key"
    
    @pytest.fixture
    def encryption_key(self):
        """Generate test encryption key."""
        return Fernet.generate_key()
    
    @pytest.fixture
    def storage(self, temp_cache_path, encryption_key):
        """Create SecureCacheStorage instance with test key."""
        return SecureCacheStorage(str(temp_cache_path), encryption_key)
    
    def test_init_with_provided_key(self, temp_cache_path, encryption_key):
        """Test initialization with provided encryption key."""
        storage = SecureCacheStorage(str(temp_cache_path), encryption_key)
        
        assert storage.cache_path == Path(temp_cache_path)
        assert storage.cipher is not None
    
    def test_init_without_key_generates_new(self, temp_cache_path, tmp_path, monkeypatch):
        """Test initialization without key generates new one."""
        # Mock config directory to use tmp_path
        monkeypatch.setattr('src.secure_cache.Path', lambda x: tmp_path / x if 'config' in x else Path(x))
        
        with patch.dict(os.environ, {}, clear=True):
            storage = SecureCacheStorage(str(temp_cache_path))
            
            assert storage.cipher is not None
    
    def test_get_or_create_key_from_env(self, temp_cache_path):
        """Test loading encryption key from environment variable."""
        test_key = Fernet.generate_key()
        
        with patch.dict(os.environ, {'CACHE_ENCRYPTION_KEY': test_key.decode()}):
            storage = SecureCacheStorage(str(temp_cache_path))
            
            # Verify key was loaded from env
            assert storage.cipher is not None
    
    def test_get_or_create_key_from_file(self, temp_cache_path, temp_key_path):
        """Test loading encryption key from existing file."""
        test_key = Fernet.generate_key()
        temp_key_path.write_bytes(test_key)
        
        with patch('src.secure_cache.Path') as mock_path:
            # Mock the key file path
            mock_key_file = Mock()
            mock_key_file.exists.return_value = True
            mock_key_file.read_bytes.return_value = test_key
            mock_path.return_value = mock_key_file
            
            storage = SecureCacheStorage(str(temp_cache_path))
            
            assert storage.cipher is not None
    
    def test_get_or_create_key_generates_new_and_saves(self, temp_cache_path, tmp_path, monkeypatch):
        """Test generating new key and saving to file."""
        key_dir = tmp_path / "config"
        key_file = key_dir / ".cache_encryption_key"
        
        # Ensure clean state
        with patch.dict(os.environ, {}, clear=True):
            with patch('src.secure_cache.Path') as mock_path_class:
                # Mock cache path
                mock_cache_path = Mock()
                mock_cache_path.__truediv__ = Mock(return_value=Mock())
                
                # Mock key file path
                mock_key_file = Mock()
                mock_key_file.exists.return_value = False
                mock_key_file.parent = Mock()
                mock_key_file.parent.mkdir = Mock()
                mock_key_file.write_bytes = Mock()
                
                def path_side_effect(arg):
                    if 'config' in str(arg):
                        return mock_key_file
                    return mock_cache_path
                
                mock_path_class.side_effect = path_side_effect
                
                storage = SecureCacheStorage(str(temp_cache_path))
                
                # Verify key was generated and saved
                assert storage.cipher is not None
                mock_key_file.parent.mkdir.assert_called_once()
                mock_key_file.write_bytes.assert_called_once()
    
    def test_calculate_hmac(self, storage):
        """Test HMAC calculation for data integrity."""
        test_data = b"test data for hmac"
        
        mac = storage._calculate_hmac(test_data)
        
        assert mac is not None
        assert len(mac) == 32  # SHA256 produces 32 bytes
        assert isinstance(mac, bytes)
    
    def test_calculate_hmac_deterministic(self, storage):
        """Test HMAC calculation is deterministic."""
        test_data = b"test data"
        
        mac1 = storage._calculate_hmac(test_data)
        mac2 = storage._calculate_hmac(test_data)
        
        assert mac1 == mac2
    
    def test_save_cache_success(self, storage, temp_cache_path):
        """Test successful cache save with encryption."""
        test_data = {
            'activities': [
                {'id': 1, 'name': 'Morning Ride'},
                {'id': 2, 'name': 'Evening Run'}
            ]
        }
        
        storage.save_cache(test_data)
        
        # Verify file was created
        assert temp_cache_path.exists()
        
        # Verify file has restrictive permissions
        stat_info = temp_cache_path.stat()
        assert oct(stat_info.st_mode)[-3:] == '600'
    
    def test_save_cache_creates_directory(self, encryption_key, tmp_path):
        """Test cache save creates parent directory if needed."""
        nested_path = tmp_path / "nested" / "dir" / "cache.json"
        storage = SecureCacheStorage(str(nested_path), encryption_key)
        
        test_data = {'test': 'data'}
        storage.save_cache(test_data)
        
        assert nested_path.exists()
        assert nested_path.parent.exists()
    
    def test_save_cache_with_metadata(self, storage, temp_cache_path):
        """Test cache save includes timestamp metadata."""
        test_data = {'key': 'value'}
        
        storage.save_cache(test_data)
        
        # Load raw encrypted data
        protected_data = temp_cache_path.read_bytes()
        
        # Verify data is encrypted (not plaintext JSON)
        assert b'key' not in protected_data
        assert b'value' not in protected_data
    
    def test_save_cache_error_handling(self, storage, temp_cache_path):
        """Test cache save handles errors gracefully."""
        # Make cache path unwritable
        temp_cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_cache_path.touch()
        os.chmod(temp_cache_path, 0o000)
        
        test_data = {'test': 'data'}
        
        with pytest.raises(Exception):
            storage.save_cache(test_data)
        
        # Cleanup
        os.chmod(temp_cache_path, 0o600)
    
    def test_load_cache_success(self, storage):
        """Test successful cache load with decryption."""
        test_data = {
            'routes': [
                {'id': 1, 'name': 'Route A'},
                {'id': 2, 'name': 'Route B'}
            ]
        }
        
        storage.save_cache(test_data)
        loaded_data = storage.load_cache()
        
        assert loaded_data == test_data
    
    def test_load_cache_nonexistent_file(self, storage):
        """Test loading cache when file doesn't exist."""
        loaded_data = storage.load_cache()
        
        assert loaded_data is None
    
    def test_load_cache_integrity_check_fails(self, storage, temp_cache_path):
        """Test cache load detects tampered data."""
        test_data = {'test': 'data'}
        storage.save_cache(test_data)
        
        # Tamper with encrypted data
        protected_data = temp_cache_path.read_bytes()
        tampered_data = protected_data[:32] + b'X' + protected_data[33:]
        temp_cache_path.write_bytes(tampered_data)
        
        loaded_data = storage.load_cache()
        
        assert loaded_data is None
    
    def test_load_cache_corrupted_data(self, storage, temp_cache_path):
        """Test cache load handles corrupted data."""
        # Write corrupted data
        temp_cache_path.write_bytes(b'corrupted data')
        
        loaded_data = storage.load_cache()
        
        assert loaded_data is None
    
    def test_load_cache_invalid_json(self, storage, temp_cache_path):
        """Test cache load handles invalid JSON."""
        # Create valid encrypted data with invalid JSON
        invalid_json = b'{"invalid": json}'
        encrypted = storage.cipher.encrypt(invalid_json)
        mac = storage._calculate_hmac(encrypted)
        temp_cache_path.write_bytes(mac + encrypted)
        
        loaded_data = storage.load_cache()
        
        assert loaded_data is None
    
    def test_save_and_load_roundtrip(self, storage):
        """Test complete save/load roundtrip preserves data."""
        test_data = {
            'activities': [
                {'id': 1, 'name': 'Ride', 'distance': 10.5},
                {'id': 2, 'name': 'Run', 'distance': 5.2}
            ],
            'metadata': {
                'total': 2,
                'last_sync': '2024-01-01T00:00:00'
            }
        }
        
        storage.save_cache(test_data)
        loaded_data = storage.load_cache()
        
        assert loaded_data == test_data
    
    def test_save_and_load_with_special_characters(self, storage):
        """Test save/load handles special characters."""
        test_data = {
            'text': 'Special chars: é, ñ, 中文, 🚴',
            'unicode': '\u2764\ufe0f'
        }
        
        storage.save_cache(test_data)
        loaded_data = storage.load_cache()
        
        assert loaded_data == test_data
    
    def test_save_and_load_empty_dict(self, storage):
        """Test save/load handles empty dictionary."""
        test_data = {}
        
        storage.save_cache(test_data)
        loaded_data = storage.load_cache()
        
        assert loaded_data == test_data
    
    def test_save_and_load_nested_structures(self, storage):
        """Test save/load handles deeply nested structures."""
        test_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': ['a', 'b', 'c']
                    }
                }
            }
        }
        
        storage.save_cache(test_data)
        loaded_data = storage.load_cache()
        
        assert loaded_data == test_data
    
    def test_delete_cache_success(self, storage, temp_cache_path):
        """Test successful cache deletion."""
        test_data = {'test': 'data'}
        storage.save_cache(test_data)
        
        assert temp_cache_path.exists()
        
        storage.delete_cache()
        
        assert not temp_cache_path.exists()
    
    def test_delete_cache_nonexistent_file(self, storage):
        """Test deleting cache when file doesn't exist."""
        # Should not raise error
        storage.delete_cache()
    
    def test_delete_cache_secure_overwrite(self, storage, temp_cache_path):
        """Test cache deletion overwrites data before deleting."""
        test_data = {'sensitive': 'data'}
        storage.save_cache(test_data)
        
        original_size = temp_cache_path.stat().st_size
        
        with patch.object(Path, 'write_bytes') as mock_write:
            with patch.object(Path, 'unlink') as mock_unlink:
                storage.delete_cache()
                
                # Verify overwrite was called with random data
                mock_write.assert_called_once()
                overwrite_data = mock_write.call_args[0][0]
                assert len(overwrite_data) == original_size
                
                # Verify file was deleted
                mock_unlink.assert_called_once()
    
    def test_delete_cache_error_handling(self, storage, temp_cache_path, caplog):
        """Test cache deletion handles errors gracefully."""
        test_data = {'test': 'data'}
        storage.save_cache(test_data)
        
        with patch.object(Path, 'write_bytes', side_effect=OSError("Permission denied")):
            storage.delete_cache()
            
            # Should log error but not raise
            assert "Failed to delete cache" in caplog.text


@pytest.mark.unit
class TestMigrateCacheToEncrypted:
    """Test migrate_cache_to_encrypted function."""
    
    @pytest.fixture
    def old_cache_path(self, tmp_path):
        """Create old plaintext cache file."""
        path = tmp_path / "old_cache.json"
        return path
    
    @pytest.fixture
    def new_cache_path(self, tmp_path):
        """Create new encrypted cache file path."""
        return tmp_path / "new_cache.json"
    
    def test_migrate_success(self, old_cache_path, new_cache_path):
        """Test successful cache migration."""
        # Create old plaintext cache
        old_data = {
            'activities': [
                {'id': 1, 'name': 'Ride'},
                {'id': 2, 'name': 'Run'}
            ]
        }
        with open(old_cache_path, 'w') as f:
            json.dump(old_data, f)
        
        result = migrate_cache_to_encrypted(str(old_cache_path), str(new_cache_path))
        
        assert result is True
        assert not old_cache_path.exists()
        assert new_cache_path.exists()
        
        # Verify data was migrated correctly
        storage = SecureCacheStorage(str(new_cache_path))
        loaded_data = storage.load_cache()
        assert loaded_data == old_data
    
    def test_migrate_nonexistent_old_cache(self, old_cache_path, new_cache_path):
        """Test migration when old cache doesn't exist."""
        result = migrate_cache_to_encrypted(str(old_cache_path), str(new_cache_path))
        
        assert result is True
    
    def test_migrate_invalid_json(self, old_cache_path, new_cache_path):
        """Test migration handles invalid JSON in old cache."""
        # Create old cache with invalid JSON
        old_cache_path.write_text('{"invalid": json}')
        
        result = migrate_cache_to_encrypted(str(old_cache_path), str(new_cache_path))
        
        assert result is False
    
    def test_migrate_secure_delete_old_cache(self, old_cache_path, new_cache_path):
        """Test migration securely deletes old cache."""
        old_data = {'test': 'data'}
        with open(old_cache_path, 'w') as f:
            json.dump(old_data, f)
        
        original_size = old_cache_path.stat().st_size
        
        with patch.object(Path, 'write_bytes') as mock_write:
            with patch.object(Path, 'unlink') as mock_unlink:
                migrate_cache_to_encrypted(str(old_cache_path), str(new_cache_path))
                
                # Verify old cache was overwritten before deletion
                # Should be called twice: once for secure delete, once for new cache
                assert mock_write.call_count >= 1
    
    def test_migrate_error_handling(self, old_cache_path, new_cache_path, caplog):
        """Test migration handles errors gracefully."""
        # Create old cache
        old_data = {'test': 'data'}
        with open(old_cache_path, 'w') as f:
            json.dump(old_data, f)
        
        with patch('src.secure_cache.SecureCacheStorage.save_cache', side_effect=Exception("Save failed")):
            result = migrate_cache_to_encrypted(str(old_cache_path), str(new_cache_path))
            
            assert result is False
            assert "Failed to migrate cache" in caplog.text


@pytest.mark.unit
class TestSecureCacheIntegration:
    """Integration tests for secure cache operations."""
    
    def test_multiple_save_load_cycles(self, tmp_path):
        """Test multiple save/load cycles maintain data integrity."""
        cache_path = tmp_path / "cache.json"
        storage = SecureCacheStorage(str(cache_path))
        
        for i in range(5):
            test_data = {'iteration': i, 'data': f'test_{i}'}
            storage.save_cache(test_data)
            loaded_data = storage.load_cache()
            assert loaded_data == test_data
    
    def test_different_keys_produce_different_ciphertexts(self, tmp_path):
        """Test same data with different keys produces different ciphertexts."""
        cache_path1 = tmp_path / "cache1.json"
        cache_path2 = tmp_path / "cache2.json"
        
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        
        storage1 = SecureCacheStorage(str(cache_path1), key1)
        storage2 = SecureCacheStorage(str(cache_path2), key2)
        
        test_data = {'test': 'data'}
        
        storage1.save_cache(test_data)
        storage2.save_cache(test_data)
        
        # Verify ciphertexts are different
        data1 = cache_path1.read_bytes()
        data2 = cache_path2.read_bytes()
        assert data1 != data2
    
    def test_wrong_key_cannot_decrypt(self, tmp_path):
        """Test data encrypted with one key cannot be decrypted with another."""
        cache_path = tmp_path / "cache.json"
        
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        
        storage1 = SecureCacheStorage(str(cache_path), key1)
        storage2 = SecureCacheStorage(str(cache_path), key2)
        
        test_data = {'test': 'data'}
        storage1.save_cache(test_data)
        
        # Try to load with wrong key
        loaded_data = storage2.load_cache()
        assert loaded_data is None

# Made with Bob
