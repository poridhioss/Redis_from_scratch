"""
Persistence Manager

Central coordinator for AOF persistence operations and recovery.
"""

import time
import threading
from typing import Optional, Dict, Any
from .config import PersistenceConfig
from .aof import AOFWriter
from .recovery import RecoveryManager


class PersistenceManager:
    """Main persistence manager coordinating AOF and recovery operations"""
    
    def __init__(self, config: Optional[PersistenceConfig] = None):
        """
        Initialize persistence manager
        
        Args:
            config: Persistence configuration (uses defaults if None)
        """
        self.config = config or PersistenceConfig()
        self.config.ensure_directories()
        
        # Initialize components
        self.aof_writer = None
        self.recovery_manager = None
        
        # State tracking
        self.last_aof_sync_time = time.time()
        
        # Threading
        self._lock = threading.Lock()
        
        # Initialize components based on configuration
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize persistence components based on configuration"""
        if self.config.aof_enabled:
            self.aof_writer = AOFWriter(
                self.config.aof_filename,
                self.config.aof_sync_policy
            )
        
        self.recovery_manager = RecoveryManager(
            self.config.aof_filename
        )
    
    def start(self) -> None:
        """Start persistence operations"""
        if self.aof_writer:
            self.aof_writer.open()
            print(f"AOF enabled: {self.config.aof_filename}")
        
        print(f"Persistence manager started with AOF enabled: {self.config.aof_enabled}")
    
    def stop(self) -> None:
        """Stop persistence operations"""
        if self.aof_writer:
            self.aof_writer.close()
        
        print("Persistence manager stopped")
    
    def recover_data(self, data_store, command_handler=None) -> bool:
        """
        Recover data on startup
        
        Args:
            data_store: Data store to populate
            command_handler: Command handler for AOF replay
            
        Returns:
            True if recovery was successful
        """
        if not self.config.get('recovery_on_startup', True):
            print("Recovery on startup disabled")
            return True
        
        if self.recovery_manager:
            return self.recovery_manager.recover_data(data_store, command_handler)
        
        return True
    
    def log_write_command(self, command: str, *args) -> None:
        """
        Log a write command (for AOF)
        
        Args:
            command: Command name
            *args: Command arguments
        """
        if self.aof_writer and self._is_write_command(command):
            self.aof_writer.log_command(command, *args)
    
    def periodic_tasks(self) -> None:
        """
        Execute periodic persistence tasks
        Should be called from the main event loop
        """
        current_time = time.time()
        
        # Handle AOF sync based on policy
        if self.aof_writer:
            if self.aof_writer.should_sync():
                self.aof_writer.sync_to_disk()
                self.last_aof_sync_time = current_time
    
    def rewrite_aof_background(self, data_store) -> bool:
        """
        Start background AOF rewrite
        
        Args:
            data_store: Current data store state
            
        Returns:
            True if rewrite process started successfully
        """
        if not self.aof_writer:
            return False
        
        try:
            def background_rewrite():
                temp_filename = self.config.get_aof_temp_filename()
                success = self.aof_writer.rewrite_aof(data_store, temp_filename)
                if success:
                    print("Background AOF rewrite completed")
                else:
                    print("Background AOF rewrite failed")
            
            thread = threading.Thread(target=background_rewrite, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            print(f"Error starting background AOF rewrite: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        return {
            'aof_enabled': self.config.aof_enabled,
            'last_aof_sync_time': int(self.last_aof_sync_time),
            'aof_filename': self.config.aof_filename if self.config.aof_enabled else None,
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
