#!/usr/bin/env python3
"""
Stop the Ride Optimizer server.

Finds and terminates the Flask server process started by launch.py.
"""

import subprocess
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_server_processes():
    """Find all running server processes."""
    try:
        # Find processes running launch.py --serve
        result = subprocess.run(
            ['pgrep', '-f', 'launch.py --serve'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = [int(pid) for pid in result.stdout.strip().split('\n')]
            return pids
        return []
    except FileNotFoundError:
        # pgrep not available, try alternative method
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            pids = []
            for line in result.stdout.split('\n'):
                if 'launch.py --serve' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pids.append(int(parts[1]))
                        except ValueError:
                            continue
            return pids
        except Exception as e:
            logger.error(f"Error finding processes: {e}")
            return []
    except Exception as e:
        logger.error(f"Error finding processes: {e}")
        return []


def stop_server(force=False):
    """Stop the server process."""
    pids = find_server_processes()
    
    if not pids:
        logger.info("No running server processes found")
        return True
    
    logger.info(f"Found {len(pids)} server process(es): {pids}")
    
    # Try graceful shutdown first
    import signal
    import os
    
    for pid in pids:
        try:
            logger.info(f"Sending SIGTERM to process {pid}...")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            logger.warning(f"Process {pid} not found")
        except PermissionError:
            logger.error(f"Permission denied to kill process {pid}")
            return False
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return False
    
    # Wait for processes to terminate
    logger.info("Waiting for processes to terminate...")
    time.sleep(2)
    
    # Check if processes are still running
    remaining_pids = find_server_processes()
    
    if remaining_pids:
        if force:
            logger.warning(f"Processes still running: {remaining_pids}")
            logger.info("Force killing remaining processes...")
            for pid in remaining_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                    logger.info(f"Force killed process {pid}")
                except Exception as e:
                    logger.error(f"Error force killing process {pid}: {e}")
            time.sleep(1)
            
            # Final check
            final_pids = find_server_processes()
            if final_pids:
                logger.error(f"Failed to stop processes: {final_pids}")
                return False
        else:
            logger.warning(f"Processes still running: {remaining_pids}")
            logger.info("Use --force to force kill")
            return False
    
    logger.info("Server stopped successfully")
    return True


def main():
    """Main entry point."""
    force = '--force' in sys.argv or '-f' in sys.argv
    
    logger.info("Stopping Ride Optimizer server...")
    
    success = stop_server(force=force)
    
    if success:
        logger.info("✓ Server stopped")
        sys.exit(0)
    else:
        logger.error("✗ Failed to stop server")
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
