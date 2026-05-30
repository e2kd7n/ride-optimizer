"""
JSON file storage utilities for Smart Static architecture.

Provides thread-safe JSON file operations with:
- Atomic writes (temp file + rename)
- File locking for concurrent access
- Proper permissions (0o600 for security)
- Graceful error handling
"""

import json
import os
import sys
import logging

if sys.platform != 'win32':
    import fcntl
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class JSONStorage:
    """
    Thread-safe JSON file storage with atomic writes.
    
    Features:
    - Atomic writes prevent corruption
    - File locking prevents race conditions
    - Automatic directory creation
    - Secure file permissions (0o600)
    - Path traversal protection
    """
    
    def __init__(self, data_dir: str = 'data'):
        """
        Initialize JSON storage.
        
        Args:
            data_dir: Directory for JSON files (default: 'data')
        """
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(exist_ok=True, mode=0o700)
        logger.info(f"JSON storage initialized: {self.data_dir}")
    
    def _validate_filename(self, filename: str) -> Path:
        """
        Validate filename to prevent path traversal attacks.
        
        Args:
            filename: Filename to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValueError: If filename is invalid or contains path traversal
        """
        # Check for path traversal attempts BEFORE sanitization
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValueError(f"Path traversal detected: filename cannot contain '..' or path separators")
        
        # Ensure it's a JSON file
        if not filename.endswith('.json'):
            raise ValueError(f"Invalid filename: must be a .json file")
        
        # Ensure no hidden files
        if filename.startswith('.'):
            raise ValueError(f"Invalid filename: hidden files not allowed")
        
        # Ensure filename is not empty
        if not filename or filename == '.json':
            raise ValueError(f"Invalid filename: empty or invalid name")
        
        # Build full path
        filepath = self.data_dir / filename
        
        # Verify resolved path is within data_dir (defense in depth - prevents symlink attacks)
        try:
            resolved = filepath.resolve()
            if not str(resolved).startswith(str(self.data_dir)):
                raise ValueError(f"Path traversal detected: resolved path outside data directory")
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")
        
        return filepath
    
    def read(self, filename: str, default: Any = None) -> Any:
        """
        Read JSON file with file locking and path validation.
        
        Args:
            filename: Name of JSON file (e.g., 'favorites.json')
            default: Default value if file doesn't exist or read fails
            
        Returns:
            Parsed JSON data or default value
        """
        # Validate filename - raises ValueError on security violations
        filepath = self._validate_filename(filename)
        
        if not filepath.exists():
            logger.debug(f"File not found: {filename}, returning default")
            return default
        
        try:
            with open(filepath, 'r') as f:
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    logger.debug(f"Successfully read {filename}")
                    return data
                finally:
                    if sys.platform != 'win32':
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            return default
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}", exc_info=True)
            return default
    
    def write(self, filename: str, data: Any) -> bool:
        """
        Write JSON file atomically with proper permissions and path validation.
        
        Uses temp file + rename for atomic writes to prevent corruption.
        
        Args:
            filename: Name of JSON file (e.g., 'favorites.json')
            data: Data to write (must be JSON-serializable)
            
        Returns:
            True if write successful, False otherwise
        """
        # Validate filename - raises ValueError on security violations
        filepath = self._validate_filename(filename)
        
        temp_path = filepath.with_suffix('.tmp')
        
        try:
            # Write to temp file
            with open(temp_path, 'w') as f:
                if sys.platform != 'win32':
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, default=str)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    if sys.platform != 'win32':
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # Set secure permissions (owner read/write only)
            os.chmod(temp_path, 0o600)
            
            # Atomic rename (replaces old file)
            temp_path.replace(filepath)
            
            logger.debug(f"Successfully wrote {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing {filename}: {e}", exc_info=True)
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False
    
    def exists(self, filename: str) -> bool:
        """
        Check if JSON file exists with path validation.
        
        Args:
            filename: Name of JSON file
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            filepath = self._validate_filename(filename)
            return filepath.exists()
        except ValueError as e:
            logger.error(f"Invalid filename '{filename}': {e}")
            return False
    
    def delete(self, filename: str) -> bool:
        """
        Delete JSON file with path validation.
        
        Args:
            filename: Name of JSON file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Validate filename - raises ValueError on security violations
        filepath = self._validate_filename(filename)
        
        try:
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {filename}: {e}")
            return False
    
    def list_files(self) -> list[str]:
        """
        List all JSON files in storage directory.
        
        Returns:
            List of JSON filenames
        """
        try:
            return [f.name for f in self.data_dir.glob('*.json')]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []


# Convenience function for quick access
_default_storage = None

def get_storage(data_dir: str = 'data') -> JSONStorage:
    """
    Get default JSONStorage instance (singleton pattern).
    
    Args:
        data_dir: Directory for JSON files
        
    Returns:
        JSONStorage instance
    """
    global _default_storage
    if _default_storage is None:
        _default_storage = JSONStorage(data_dir)
    return _default_storage


