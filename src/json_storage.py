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
import time
from src.secure_logger import SecureLogger
import threading
from contextlib import contextmanager

if sys.platform != 'win32':
    import fcntl
else:
    import msvcrt
from pathlib import Path
from typing import Any, Callable
from datetime import datetime

logger = SecureLogger(__name__)
# Per-file in-process locks, keyed by resolved file path. Module-level (not
# per-instance) because several services construct their own JSONStorage over
# the same data dir — instance-level locks would not exclude each other.
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()

# Parsed-JSON read cache keyed by resolved file path, invalidated by file
# (mtime_ns, size). Module-level for the same reason as _THREAD_LOCKS: all
# JSONStorage instances over the same file share one cached parse. This
# exists for the large hot files (route_groups.json is ~12MB on disk) that
# were being re-read and re-parsed on every API request (#461).
_READ_CACHE: dict[str, tuple] = {}
_READ_CACHE_GUARD = threading.Lock()


if sys.platform == 'win32':
    def _msvcrt_lock_blocking(fd: int) -> None:
        """
        Lock byte 0 of *fd*, blocking indefinitely until acquired.

        msvcrt.locking's own LK_LOCK mode is *not* an indefinite block like
        fcntl.flock: per the msvcrt docs it retries only 10 times, roughly a
        second apart, then raises OSError — under real contention (e.g. a
        writer that briefly holds the lock across a slow fsync+rename) that
        cap can be hit, and a caller not expecting a raise there would drop
        the write it was about to make. Poll with the non-blocking LK_NBLCK
        mode ourselves instead, so this call has the same "block until
        acquired" contract as fcntl.flock(LOCK_EX).
        """
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.01)


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
        Exclusive per-file lock: a threading.Lock within the process plus an
        OS-level lock on a sidecar ``<name>.lock`` file across processes
        (cron jobs and gunicorn workers are separate processes on the Pi).

        The OS lock goes on a sidecar file rather than the data file because
        atomic writes replace the data file's inode on rename — a lock held
        on the old inode would not exclude writers that open the new one.

        Cross-process locking mechanism differs by platform:
        - POSIX (production/Pi): fcntl.flock on the sidecar file.
        - Windows (local dev): msvcrt.locking on the sidecar file. Windows
          has no flock-a-whole-file primitive, so this locks a single byte
          at offset 0 instead — sufficient since the sidecar file's only
          purpose is to be lockable, not to hold data.

        Note on why this is needed at all despite gunicorn.conf.py defaulting
        GUNICORN_WORKERS to 1: a single worker already makes the POSIX fcntl
        path's cross-process guarantee somewhat academic in production (one
        process, so the threading.Lock above would suffice there too) — but
        gunicorn itself requires fork() and doesn't run on Windows at all, so
        this path is exercised only by local Windows dev (`python launch.py`)
        plus the test suite. There, cross-process safety isn't about worker
        count but about guarding against e.g. a second `launch.py` accidentally
        left running, or a test process racing the dev server — hence a real
        OS-level lock rather than relying solely on the in-process
        threading.Lock, which cannot exclude a different process.
        """
        with _THREAD_LOCKS_GUARD:
            tlock = _THREAD_LOCKS.setdefault(str(filepath), threading.Lock())
        with tlock:
            lock_path = filepath.parent / (filepath.name + '.lock')
            with open(lock_path, 'a') as lf:
                secure_chmod(lock_path)
                if sys.platform != 'win32':
                    fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                else:
                    # msvcrt.locking locks nbytes starting at the current
                    # file position, and requires those bytes to already
                    # exist in the file — so make sure there's at least one
                    # byte to lock before seeking to it.
                    if os.fstat(lf.fileno()).st_size == 0:
                        lf.write(' ')
                        lf.flush()
                    lf.seek(0)
                    _msvcrt_lock_blocking(lf.fileno())
                try:
                    yield
                finally:
                    if sys.platform != 'win32':
                        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
                    else:
                        lf.seek(0)
                        msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)

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
                else:
                    # msvcrt has no shared-lock mode, so this is exclusive —
                    # slightly more conservative than POSIX LOCK_SH, but reads
                    # are quick and this only blocks other readers/writers of
                    # this exact fd's lock byte, not the sidecar lock used by
                    # write()/update() (see _locked()'s docstring).
                    if os.fstat(f.fileno()).st_size > 0:
                        _msvcrt_lock_blocking(f.fileno())
                        f.seek(0)
                try:
                    data = json.load(f)
                    logger.debug(f"Successfully read {filename}")
                    return data
                finally:
                    if sys.platform != 'win32':
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    elif os.fstat(f.fileno()).st_size > 0:
                        f.seek(0)
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            return default
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}", exc_info=True)
            return default

    def read_cached(self, filename: str, default: Any = None) -> Any:
        """
        Read JSON with an in-process cache invalidated by file (mtime, size).

        Repeated calls return the same parsed object until the file changes
        on disk (writes through JSONStorage rename the file, which bumps the
        mtime and invalidates naturally). Use for large, frequently-read,
        rarely-written files where a per-request re-parse is the bottleneck.

        The returned object is SHARED across callers and threads — treat it
        as read-only. Copy before sorting or mutating.
        """
        filepath = self._validate_filename(filename)
        key = str(filepath)

        try:
            st = filepath.stat()
        except OSError:
            # Missing file: drop any stale entry so a later recreate re-reads
            with _READ_CACHE_GUARD:
                _READ_CACHE.pop(key, None)
            return default
        stamp = (st.st_mtime_ns, st.st_size)

        with _READ_CACHE_GUARD:
            hit = _READ_CACHE.get(key)
            if hit is not None and hit[0] == stamp:
                return hit[1]

        data = self.read(filename, default=default)
        # Don't cache failures/defaults — let the next call retry the read
        if data is not default:
            with _READ_CACHE_GUARD:
                _READ_CACHE[key] = (stamp, data)
        return data

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


