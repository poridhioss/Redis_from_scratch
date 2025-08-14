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
            # AOF Configuration
            'aof_enabled': True,
            'aof_filename': 'appendonly.aof',
            'aof_sync_policy': 'everysec',  # 'always', 'everysec', 'no'
            'aof_rewrite_percentage': 100,  # Auto rewrite when AOF is 100% larger
            'aof_rewrite_min_size': 1024 * 1024,  # Minimum AOF size for rewrite (1MB)
            
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
        # Validate AOF sync policy
        valid_sync_policies = ['always', 'everysec', 'no']
        if self._config['aof_sync_policy'] not in valid_sync_policies:
            raise ValueError(f"Invalid AOF sync policy. Must be one of: {valid_sync_policies}")
        
        # Validate file paths
        if not self._config['aof_filename']:
            raise ValueError("AOF filename cannot be empty")
    
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
    def aof_enabled(self) -> bool:
        return self._config['aof_enabled']
    
    @property
    def aof_filename(self) -> str:
        return os.path.join(self._config['data_dir'], self._config['aof_filename'])
    
    @property
    def aof_sync_policy(self) -> str:
        return self._config['aof_sync_policy']
    
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
    
    def get_aof_temp_filename(self) -> str:
        """Get temporary AOF filename for rewrite operations"""
        return os.path.join(self.temp_dir, f"temp-rewrite-aof-{int(time.time())}.aof")
    
    def __repr__(self) -> str:
        """String representation of configuration"""
        return f"PersistenceConfig({self._config})"
