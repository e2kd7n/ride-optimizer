"""
Route Loader Service

Handles loading route data from JSON cache files.

Copyright (c) 2024-2026 e2kd7n
Licensed under the MIT License - see LICENSE file for details.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RouteLoader:
    """
    Loads route data from JSON storage files.
    
    Responsible only for file I/O. Does not perform filtering, sorting, or
    any business logic transformation.
    """
    
    def __init__(self, data_dir: str = 'data'):
        """
        Initialize RouteLoader.
        
        Args:
            data_dir: Directory containing route data JSON files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.commute_routes_file = self.data_dir / 'route_groups.json'
        self.long_rides_file = self.data_dir / 'long_rides.json'
        self.status_file = self.data_dir / 'status.json'
    
    def load_commute_routes(self) -> List[Dict[str, Any]]:
        """
        Load commute route groups from cache.
        
        Returns:
            List of route group dictionaries, or empty list if file not found
        """
        if not self.commute_routes_file.exists():
            logger.warning(f"Commute routes file not found: {self.commute_routes_file}")
            return []
        
        try:
            with open(self.commute_routes_file, 'r') as f:
                data = json.load(f)
            
            routes = data.get('route_groups', []) if isinstance(data, dict) else data
            logger.info(f"Loaded {len(routes)} commute routes from {self.commute_routes_file}")
            return routes
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse commute routes JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load commute routes: {e}")
            return []
    
    def load_long_rides(self) -> List[Dict[str, Any]]:
        """
        Load long ride data from cache.
        
        Returns:
            List of long ride dictionaries, or empty list if file not found
        """
        if not self.long_rides_file.exists():
            logger.warning(f"Long rides file not found: {self.long_rides_file}")
            return []
        
        try:
            with open(self.long_rides_file, 'r') as f:
                data = json.load(f)
            
            rides = data.get('long_rides', []) if isinstance(data, dict) else data
            logger.info(f"Loaded {len(rides)} long rides from {self.long_rides_file}")
            return rides
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse long rides JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to load long rides: {e}")
            return []
    
    def load_status(self) -> Dict[str, Any]:
        """
        Load system status information.
        
        Returns:
            Status dictionary, or empty dict if file not found
        """
        if not self.status_file.exists():
            logger.debug(f"Status file not found: {self.status_file}")
            return {}
        
        try:
            with open(self.status_file, 'r') as f:
                status = json.load(f)
            logger.debug(f"Loaded status from {self.status_file}")
            return status
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse status JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load status: {e}")
            return {}
    
    def save_commute_routes(self, routes: List[Dict[str, Any]]) -> bool:
        """
        Save commute routes to cache.
        
        Args:
            routes: List of route dictionaries to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {'route_groups': routes, 'version': '1.0'}
            with open(self.commute_routes_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(routes)} commute routes to {self.commute_routes_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save commute routes: {e}")
            return False
    
    def save_long_rides(self, rides: List[Dict[str, Any]]) -> bool:
        """
        Save long rides to cache.
        
        Args:
            rides: List of ride dictionaries to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {'long_rides': rides, 'version': '1.0'}
            with open(self.long_rides_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(rides)} long rides to {self.long_rides_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save long rides: {e}")
            return False
    
    def save_status(self, status: Dict[str, Any]) -> bool:
        """
        Save system status information.
        
        Args:
            status: Status dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
            logger.debug(f"Saved status to {self.status_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save status: {e}")
            return False
