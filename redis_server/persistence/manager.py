"""
Persistence Manager

Central coordinator for RDB persistence operations and recovery.
"""

import time
import threading
from typing import Optional, Dict, Any
from .config import PersistenceConfig
from .rdb import RDBHandler
from .recovery import RecoveryManager


class PersistenceManager:
    """Main persistence manager coordinating RDB and recovery operations"""
    
    def __init__(self, config: Optional[PersistenceConfig] = None):
        """
        Initialize persistence manager
        
        Args:
            config: Persistence configuration (uses defaults if None)
        """
        self.config = config or PersistenceConfig()
        self.config.ensure_directories()
        
        # Initialize components
        self.rdb_handler = None
        self.recovery_manager = None
        
        # State tracking
        self.changes_since_save = 0
        self.last_rdb_save_time = time.time()
        
        # Threading
        self._lock = threading.Lock()
        
        # Initialize components based on configuration
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize persistence components based on configuration"""
        if self.config.rdb_enabled:
            self.rdb_handler = RDBHandler(
                self.config.rdb_filename,
                self.config.get('rdb_compression', True),
                self.config.get('rdb_checksum', True)
            )
        
        self.recovery_manager = RecoveryManager(
            self.config.rdb_filename
        )
    
    def start(self) -> None:
        """Start persistence operations"""
        if self.rdb_handler:
            print(f"RDB enabled: {self.config.rdb_filename}")
        
        print(f"Persistence manager started with RDB enabled: {self.config.rdb_enabled}")
    
    def stop(self) -> None:
        """Stop persistence operations"""
        print("Persistence manager stopped")
    
    def recover_data(self, data_store, command_handler=None) -> bool:
        """
        Recover data on startup
        
        Args:
            data_store: Data store to populate
            command_handler: Command handler (not used for RDB)
            
        Returns:
            True if recovery was successful
        """
        if not self.config.get('recovery_on_startup', True):
            print("Recovery on startup disabled")
            return True
        
        if self.recovery_manager:
            return self.recovery_manager.recover_data(data_store)
        
        return True
    
    def log_write_command(self, command: str, *args) -> None:
        """
        Track write commands for RDB save triggers
        
        Args:
            command: Command name
            *args: Command arguments
        """
        if self._is_write_command(command):
            self.changes_since_save += 1
    
    def periodic_tasks(self) -> None:
        """
        Execute periodic persistence tasks
        Should be called from the main event loop
        """
        current_time = time.time()
        
        # Handle automatic RDB saves
        if self.rdb_handler:
            if self.config.should_auto_rdb_save(self.changes_since_save, self.last_rdb_save_time):
                print(f"Auto-saving RDB: {self.changes_since_save} changes in {current_time - self.last_rdb_save_time:.1f}s")
                if self.create_rdb_snapshot_background():
                    self.changes_since_save = 0
                    self.last_rdb_save_time = current_time
    
    def create_rdb_snapshot(self, data_store) -> bool:
        """
        Create synchronous RDB snapshot
        
        Args:
            data_store: Current data store state
            
        Returns:
            True if successful
        """
        if not self.rdb_handler:
            return False
        
        success = self.rdb_handler.create_snapshot(data_store)
        if success:
            self.last_rdb_save_time = time.time()
            self.changes_since_save = 0
        
        return success
    
    def create_rdb_snapshot_background(self, data_store=None) -> bool:
        """
        Create background RDB snapshot
        
        Args:
            data_store: Current data store state
            
        Returns:
            True if background process started successfully
        """
        if not self.rdb_handler:
            return False
        
        return self.rdb_handler.create_background_snapshot(data_store)
    
    def get_last_save_time(self) -> int:
        """Get timestamp of last RDB save"""
        if self.rdb_handler:
            return self.rdb_handler.get_last_save_time()
        return int(self.last_rdb_save_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        return {
            'rdb_enabled': self.config.rdb_enabled,
            'changes_since_save': self.changes_since_save,
            'last_rdb_save_time': self.get_last_save_time(),
            'rdb_filename': self.config.rdb_filename if self.config.rdb_enabled else None,
        }
    
    def _is_write_command(self, command: str) -> bool:
        """
        Check if command is a write command that should be logged
        
        Args:
            command: Command name
            
        Returns:
            True if it's a write command
        """
        write_commands = {
            'SET', 'DEL', 'EXPIRE', 'EXPIREAT', 'PERSIST', 'FLUSHALL',
            'SETEX', 'SETNX', 'MSET', 'MSETNX', 'APPEND', 'INCR', 'DECR',
            'INCRBY', 'DECRBY', 'LPUSH', 'RPUSH', 'LPOP', 'RPOP', 'SADD',
            'SREM', 'SPOP', 'HSET', 'HDEL', 'HINCRBY', 'ZADD', 'ZREM'
        }
        return command.upper() in write_commands
