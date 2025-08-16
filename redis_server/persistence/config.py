"""
Persistence Configuration Management

Handles all configuration related to data persistence including AOF and RDB settings.
"""

import os
import time
from typing import List, Tuple, Dict, Any


class PersistenceConfig:
    """Configuration class for Redis persistence settings"""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize persistence configuration
        
        Args:
            config_dict: Dictionary containing configuration options
        """
        # Set default configuration
        self._config = self._get_default_config()
        
        # Update with provided configuration
        if config_dict:
            self._config.update(config_dict)
        
        # Validate configuration
        self._validate_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default persistence configuration"""
        return {
            # RDB Configuration
            'rdb_enabled': True,
            'rdb_filename': 'dump.rdb',
            'rdb_compression': True,
            'rdb_checksum': True,
            
            # RDB Save Conditions: (seconds, changes)
            'rdb_save_conditions': [
                (900, 1),     # Save if 1 key changed in 900 seconds (15 min)
                (300, 10),    # Save if 10 keys changed in 300 seconds (5 min)
                (60, 10000),  # Save if 10000 keys changed in 60 seconds (1 min)
            ],
            
            # Directory Configuration
            'data_dir': './data',
            'temp_dir': './data/temp',
            
            # General Settings
            'persistence_enabled': True,
            'recovery_on_startup': True,
            'max_memory_usage': 100 * 1024 * 1024,  # 100MB max memory
        }
    
    def _validate_config(self) -> None:
        """Validate configuration values"""
        # Validate RDB save conditions
        for condition in self._config['rdb_save_conditions']:
            if not isinstance(condition, tuple) or len(condition) != 2:
                raise ValueError("RDB save conditions must be tuples of (seconds, changes)")
            if not isinstance(condition[0], int) or not isinstance(condition[1], int):
                raise ValueError("RDB save conditions must contain integer values")
        
        # Validate file paths
        if not self._config['rdb_filename']:
            raise ValueError("RDB filename cannot be empty")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._config[key] = value
        self._validate_config()
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update multiple configuration values"""
        self._config.update(config_dict)
        self._validate_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self._config.copy()
    
    # Convenience properties for frequently accessed settings
    @property
    def rdb_enabled(self) -> bool:
        return self._config['rdb_enabled']
    
    @property
    def rdb_filename(self) -> str:
        return os.path.join(self._config['data_dir'], self._config['rdb_filename'])
    
    @property
    def rdb_save_conditions(self) -> List[Tuple[int, int]]:
        return self._config['rdb_save_conditions']
    
    @property
    def data_dir(self) -> str:
        return self._config['data_dir']
    
    @property
    def temp_dir(self) -> str:
        return self._config['temp_dir']
    
    def ensure_directories(self) -> None:
        """Ensure data and temp directories exist"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def should_auto_rdb_save(self, changes: int, last_save_time: float) -> bool:
        """
        Check if RDB should be automatically saved based on conditions
        
        Args:
            changes: Number of changes since last save
            last_save_time: Timestamp of last save
            
        Returns:
            True if RDB should be saved
        """
        if not self.rdb_enabled:
            return False
        
        current_time = time.time()
        elapsed = current_time - last_save_time
        
        for seconds, required_changes in self.rdb_save_conditions:
            if elapsed >= seconds and changes >= required_changes:
                return True
        
        return False
    
    def get_rdb_temp_filename(self) -> str:
        """Get temporary RDB filename for background saves"""
        return os.path.join(self.temp_dir, f"temp-{int(time.time())}.rdb")
    
    def __repr__(self) -> str:
        """String representation of configuration"""
        return f"PersistenceConfig({self._config})"
