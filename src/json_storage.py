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
from src.secure_logger import SecureLogger
import threading
from contextlib import contextmanager

if sys.platform != 'win32':
    import fcntl
from pathlib import Path
from typing import Any, Callable
from datetime import datetime

logger = SecureLogger(__name__)
# Per-file in-process locks, keyed by resolved file path. Module-level (not
# per-instance) because several services construct their own JSONStorage over
# the same data dir — instance-level locks would not exclude each other.
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def secure_chmod(path) -> None:
    """
    Best-effort chmod to 0o600 (owner read/write only).

    Several cache writers under src/ bypass JSONStorage and write JSON
    directly with plain `open()`, leaving files at the process umask's
    default permissions. Call this right after writing to bring them to the
    same owner-only baseline JSONStorage already provides. No-op on
    platforms/filesystems that don't support POSIX permission bits (e.g.
    Windows, FAT32).
    """
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


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

    @contextmanager
    def _locked(self, filepath: Path):
        """
        Exclusive per-file lock: a threading.Lock within the process plus
        flock on a sidecar ``<name>.lock`` file across processes (POSIX only;
        cron jobs and gunicorn workers are separate processes).

        The flock goes on a sidecar file rather than the data file because
        atomic writes replace the data file's inode on rename — a lock held
        on the old inode would not exclude writers that open the new one.
        """
        with _THREAD_LOCKS_GUARD:
            tlock = _THREAD_LOCKS.setdefault(str(filepath), threading.Lock())
        with tlock:
            lock_path = filepath.parent / (filepath.name + '.lock')
            with open(lock_path, 'a') as lf:
                secure_chmod(lock_path)
                if sys.platform != 'win32':
                    fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    if sys.platform != 'win32':
                        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

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

        with self._locked(filepath):
            return self._write_locked(filepath, data)

    def _write_locked(self, filepath: Path, data: Any) -> bool:
        """Atomic temp-file + rename write. Caller must hold ``_locked``."""
        temp_path = filepath.with_suffix('.tmp')

        try:
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            # Set secure permissions (owner read/write only)
            os.chmod(temp_path, 0o600)

            # Atomic rename (replaces old file)
            temp_path.replace(filepath)

            logger.debug(f"Successfully wrote {filepath.name}")
            return True

        except Exception as e:
            logger.error(f"Error writing {filepath.name}: {e}", exc_info=True)
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            return False

    def update(self, filename: str, mutator: Callable[[Any], Any],
               default: Any = None) -> tuple[bool, Any]:
        """
        Atomic read-modify-write under a single exclusive lock.

        Separate read()/write() calls are each safe individually, but two
        concurrent read-modify-write sequences can both read the same state
        and the second write silently discards the first's change. This
        method holds the lock across the whole sequence.

        Args:
            filename: Name of JSON file (e.g., 'saved_plans.json')
            mutator: Called with the current contents (or ``default`` if the
                file is missing/unreadable); returns the new contents to
                persist. Exceptions from the mutator propagate and nothing
                is written.
            default: Value passed to the mutator when there is no readable
                current state

        Returns:
            Tuple of (write succeeded, data returned by the mutator)
        """
        filepath = self._validate_filename(filename)

        with self._locked(filepath):
            data = default
            if filepath.exists():
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    logger.error(f"Error reading {filename} during update: {e}")

            new_data = mutator(data)
            success = self._write_locked(filepath, new_data)

        return success, new_data

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


