"""
Append-Only File (AOF) Implementation

Handles logging of write commands to disk for data persistence and recovery.
"""

import os
import time
import threading
import shutil

class AOFWriter:
    """Handles AOF (Append-Only File) operations for command logging"""
    
    def __init__(self, filename: str, sync_policy: str = 'everysec'):
        """
        Initialize AOF writer
        
        Args:
            filename: Path to AOF file
            sync_policy: Sync policy ('always', 'everysec', 'no')
        """
        self.filename = filename
        self.sync_policy = sync_policy
        self.file_handle = None
        self.last_sync_time = time.time()
        self.pending_writes = 0
        self._lock = threading.Lock()
        
        # Write commands that should be logged
        self.write_commands = {
            'SET', 'DEL', 'EXPIRE', 'EXPIREAT', 'PERSIST', 'FLUSHALL'
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    def open(self) -> None:
        """Open AOF file for writing"""
        try:
            self.file_handle = open(self.filename, 'a', encoding='utf-8')
        except IOError as e:
            raise RuntimeError(f"Failed to open AOF file {self.filename}: {e}")
    
    def close(self) -> None:
        """Close AOF file"""
        if self.file_handle:
            self.sync_to_disk()  # Final sync before closing
            self.file_handle.close()
            self.file_handle = None
    
    def log_command(self, command: str, *args) -> None:
        """
        Log a command to the AOF file
        
        Args:
            command: Command name (e.g., 'SET', 'DEL')
            *args: Command arguments
        """
        if not self.file_handle or command.upper() not in self.write_commands:
            return
        
        with self._lock:
            try:
                # Format command in Redis protocol format
                formatted_command = self._format_command(command, *args)
                self.file_handle.write(formatted_command)
                self.pending_writes += 1
                
                # Sync based on policy
                if self.sync_policy == 'always':
                    self.file_handle.flush()
                    os.fsync(self.file_handle.fileno())
                    self.last_sync_time = time.time()
                    self.pending_writes = 0
                    
            except IOError as e:
                print(f"Error writing to AOF file: {e}")
    
    def _format_command(self, command: str, *args) -> str:
        """Format command in Redis protocol format for AOF"""
        # Simple text format for AOF (easier to read and debug)
        timestamp = int(time.time())
        formatted_args = ' '.join(str(arg) for arg in args)
        return f"{timestamp} {command.upper()} {formatted_args}\n"
    
    def sync_to_disk(self) -> None:
        """Force sync to disk based on policy"""
        if not self.file_handle or self.pending_writes == 0:
            return
            
        with self._lock:
            try:
                self.file_handle.flush()
                os.fsync(self.file_handle.fileno())
                self.last_sync_time = time.time()
                self.pending_writes = 0
            except IOError as e:
                print(f"Error syncing AOF file: {e}")
    
    def should_sync(self) -> bool:
        """Check if file should be synced based on policy"""
        if self.sync_policy == 'always':
            return False  # Already synced immediately
        elif self.sync_policy == 'everysec':
            return time.time() - self.last_sync_time >= 1.0
        else:  # 'no'
            return False
    
    def rewrite_aof(self, data_store, temp_filename: str) -> bool:
        """
        Create a compacted version of the AOF file
        
        Args:
            data_store: Current data store state
            temp_filename: Temporary file to write to
            
        Returns:
            True if rewrite was successful
        """
        try:
            with open(temp_filename, 'w', encoding='utf-8') as temp_file:
                current_time = int(time.time())
                
                # Write all current keys as SET commands
                for key in data_store.keys():
                    value = data_store.get(key)
                    if value is not None:
                        # Get TTL if exists
                        ttl = data_store.ttl(key)
                        
                        # Write SET command
                        temp_file.write(f"{current_time} SET {key} {value}\n")
                        
                        # Write EXPIRE command if TTL exists
                        if ttl > 0:
                            temp_file.write(f"{current_time} EXPIRE {key} {ttl}\n")
            
            # Atomically replace original file
            shutil.move(temp_filename, self.filename)
            
            # Reopen file handle if it was open
            if self.file_handle:
                self.file_handle.close()
                self.open()
            
            return True
            
        except Exception as e:
            print(f"Error during AOF rewrite: {e}")
            # Clean up temp file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return False
    
    def get_file_size(self) -> int:
        """Get current AOF file size"""
        try:
            return os.path.getsize(self.filename)
        except OSError:
            return 0
    
    def needs_rewrite(self, min_size: int, percentage: int) -> bool:
        """
        Check if AOF needs rewriting based on size thresholds
        
        Args:
            min_size: Minimum size before considering rewrite
            percentage: Percentage growth that triggers rewrite
            
        Returns:
            True if AOF should be rewritten
        """
        current_size = self.get_file_size()
        if current_size < min_size:
            return False
        
        # For now, trigger rewrite if file is larger than min_size * 2
        # In a real implementation, we'd compare with last rewrite size
        return current_size > min_size * 2
