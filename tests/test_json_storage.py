"""
Unit tests for JSONStorage utility.

Tests atomic writes, file locking, permissions, and error handling.
"""

import pytest
import json
import os
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from src.json_storage import JSONStorage, get_storage


class TestJSONStorage:
    """Test suite for JSONStorage class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create JSONStorage instance with temp directory."""
        return JSONStorage(data_dir=temp_dir)
    
    def test_initialization(self, temp_dir):
        """Test storage initialization creates directory."""
        storage = JSONStorage(data_dir=temp_dir)
        assert Path(temp_dir).exists()
        assert Path(temp_dir).is_dir()
    
    def test_write_and_read(self, storage):
        """Test basic write and read operations."""
        test_data = {'key': 'value', 'number': 42}
        
        # Write data
        success = storage.write('test.json', test_data)
        assert success is True
        
        # Read data
        read_data = storage.read('test.json')
        assert read_data == test_data
    
    def test_read_nonexistent_file(self, storage):
        """Test reading non-existent file returns default."""
        default = {'default': True}
        result = storage.read('nonexistent.json', default=default)
        assert result == default
    
    def test_read_nonexistent_file_no_default(self, storage):
        """Test reading non-existent file with no default returns None."""
        result = storage.read('nonexistent.json')
        assert result is None
    
    def test_atomic_write(self, storage, temp_dir):
        """Test atomic write creates temp file then renames."""
        test_data = {'atomic': True}
        
        storage.write('atomic.json', test_data)
        
        # Verify final file exists
        final_path = Path(temp_dir) / 'atomic.json'
        assert final_path.exists()
        
        # Verify temp file doesn't exist
        temp_path = Path(temp_dir) / 'atomic.tmp'
        assert not temp_path.exists()
    
    def test_file_permissions(self, storage, temp_dir):
        """Test files are created with secure permissions (0o600)."""
        test_data = {'secure': True}
        storage.write('secure.json', test_data)
        
        file_path = Path(temp_dir) / 'secure.json'
        file_stat = file_path.stat()
        
        # Check permissions (owner read/write only)
        assert oct(file_stat.st_mode)[-3:] == '600'
    
    def test_overwrite_existing_file(self, storage):
        """Test overwriting existing file."""
        # Write initial data
        storage.write('overwrite.json', {'version': 1})
        
        # Overwrite with new data
        new_data = {'version': 2}
        success = storage.write('overwrite.json', new_data)
        assert success is True
        
        # Verify new data
        read_data = storage.read('overwrite.json')
        assert read_data == new_data
    
    def test_complex_data_types(self, storage):
        """Test writing complex data types."""
        test_data = {
            'string': 'hello',
            'number': 42,
            'float': 3.14,
            'boolean': True,
            'null': None,
            'list': [1, 2, 3],
            'nested': {
                'key': 'value'
            }
        }
        
        storage.write('complex.json', test_data)
        read_data = storage.read('complex.json')
        
        assert read_data == test_data
    
    def test_datetime_serialization(self, storage):
        """Test datetime objects are serialized to strings."""
        test_data = {
            'timestamp': datetime.now(),
            'date': datetime.now().date()
        }
        
        storage.write('datetime.json', test_data)
        read_data = storage.read('datetime.json')
        
        # Datetimes should be converted to strings
        assert isinstance(read_data['timestamp'], str)
        assert isinstance(read_data['date'], str)
    
    def test_exists(self, storage):
        """Test exists method."""
        # Non-existent file
        assert storage.exists('nonexistent.json') is False
        
        # Create file
        storage.write('exists.json', {'test': True})
        
        # File should exist
        assert storage.exists('exists.json') is True
    
    def test_delete(self, storage):
        """Test delete method."""
        # Create file
        storage.write('delete.json', {'test': True})
        assert storage.exists('delete.json') is True
        
        # Delete file
        success = storage.delete('delete.json')
        assert success is True
        assert storage.exists('delete.json') is False
    
    def test_delete_nonexistent(self, storage):
        """Test deleting non-existent file returns False."""
        success = storage.delete('nonexistent.json')
        assert success is False
    
    def test_list_files(self, storage):
        """Test listing JSON files."""
        # Create multiple files
        storage.write('file1.json', {'id': 1})
        storage.write('file2.json', {'id': 2})
        storage.write('file3.json', {'id': 3})
        
        files = storage.list_files()
        
        assert len(files) == 3
        assert 'file1.json' in files
        assert 'file2.json' in files
        assert 'file3.json' in files
    
    def test_invalid_json_read(self, storage, temp_dir):
        """Test reading invalid JSON returns default."""
        # Create invalid JSON file
        invalid_path = Path(temp_dir) / 'invalid.json'
        invalid_path.write_text('{ invalid json }')
        
        default = {'error': True}
        result = storage.read('invalid.json', default=default)
        
        assert result == default
    
    def test_update_creates_file_from_default(self, storage):
        """Test update on a missing file passes default to the mutator."""
        success, result = storage.update(
            'plans.json', lambda plans: plans + [{'id': 'a'}], default=[]
        )
        assert success is True
        assert result == [{'id': 'a'}]
        assert storage.read('plans.json') == [{'id': 'a'}]

    def test_update_mutates_existing_data(self, storage):
        """Test update reads current contents and persists mutator result."""
        storage.write('counter.json', {'count': 1})

        def increment(data):
            data['count'] += 1
            return data

        success, result = storage.update('counter.json', increment)
        assert success is True
        assert result == {'count': 2}
        assert storage.read('counter.json') == {'count': 2}

    def test_update_mutator_exception_leaves_file_untouched(self, storage):
        """Test a raising mutator propagates and writes nothing."""
        storage.write('safe.json', {'v': 1})

        def boom(data):
            raise RuntimeError('mutator failed')

        with pytest.raises(RuntimeError):
            storage.update('safe.json', boom)

        assert storage.read('safe.json') == {'v': 1}

    def test_update_invalid_filename(self, storage):
        """Test update validates filenames like read/write."""
        with pytest.raises(ValueError):
            storage.update('../evil.json', lambda d: d, default={})

    def test_get_storage_singleton(self, temp_dir):
        """Test get_storage returns singleton instance."""
        storage1 = get_storage(temp_dir)
        storage2 = get_storage(temp_dir)
        
        # Should be same instance
        assert storage1 is storage2


@pytest.mark.integration
class TestJSONStorageConcurrency:
    """Test concurrent access to JSON storage."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create JSONStorage instance with temp directory."""
        return JSONStorage(data_dir=temp_dir)
    
    def test_concurrent_writes(self, storage):
        """Test multiple writes don't corrupt data."""
        # Simulate concurrent writes
        for i in range(10):
            data = {'iteration': i, 'timestamp': datetime.now().isoformat()}
            success = storage.write('concurrent.json', data)
            assert success is True
        
        # Verify final data is valid JSON
        final_data = storage.read('concurrent.json')
        assert final_data is not None
        assert 'iteration' in final_data

    def test_concurrent_updates_lose_no_increments(self, storage):
        """Test racing read-modify-write updates don't drop each other's writes.

        This is the lost-update scenario from issue #459: with separate
        read()+write() calls, concurrent threads read the same state and the
        last write wins. update() must serialize the whole sequence.
        """
        import threading

        storage.write('shared.json', {'count': 0})
        n_threads, n_iterations = 8, 25

        def worker():
            for _ in range(n_iterations):
                def increment(data):
                    data['count'] += 1
                    return data
                storage.update('shared.json', increment)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert storage.read('shared.json') == {'count': n_threads * n_iterations}


