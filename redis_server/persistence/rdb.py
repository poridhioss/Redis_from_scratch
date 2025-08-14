"""
Redis Database (RDB) Implementation

Handles creating and loading binary snapshots of the database state.
"""

import os
import time
import pickle
import subprocess
import threading
import hashlib
import gzip
import tempfile
import shutil
from typing import Dict, Any, Optional


class RDBHandler:
    """Handles RDB (Redis Database) snapshot operations"""
    
    # RDB file format constants
    MAGIC_STRING = b'REDIS'
    VERSION = b'0001'
    
    def __init__(self, filename: str, compression: bool = True, checksum: bool = True):
        """
        Initialize RDB handler
        
        Args:
            filename: Path to RDB file
            compression: Enable compression
            checksum: Enable checksum verification
        """
        self.filename = filename
        self.compression = compression
        self.checksum = checksum
        self.last_save_time = 0
        self._lock = threading.Lock()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    def create_snapshot(self, data_store) -> bool:
        """
        Create a synchronous RDB snapshot
        
        Args:
            data_store: Current data store state
            
        Returns:
            True if snapshot was created successfully
        """
        with self._lock:
            try:
                temp_filename = f"{self.filename}.tmp"
                
                # Serialize data
                data = self._extract_data_store_state(data_store)
                binary_data = self._serialize_data(data)
                
                # Write to temporary file
                with open(temp_filename, 'wb') as f:
                    f.write(binary_data)
                
                # Atomically replace original file
                shutil.move(temp_filename, self.filename)
                self.last_save_time = time.time()
                
                print(f"RDB snapshot saved to {self.filename}")
                return True
                
            except Exception as e:
                print(f"Error creating RDB snapshot: {e}")
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                return False
    
    def create_background_snapshot(self, data_store) -> bool:
        """
        Create a background RDB snapshot using subprocess
        
        Args:
            data_store: Current data store state
            
        Returns:
            True if background process started successfully
        """
        try:
            # For this implementation, we'll use threading instead of subprocess
            # In production, Redis uses fork()
            def background_save():
                success = self.create_snapshot(data_store)
                if success:
                    print("Background RDB save completed")
                else:
                    print("Background RDB save failed")
            
            thread = threading.Thread(target=background_save, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            print(f"Error starting background RDB save: {e}")
            return False
    
    def load_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Load RDB snapshot from file
        
        Returns:
            Dictionary containing the loaded data or None if file doesn't exist
        """
        if not self.file_exists():
            return None
        
        try:
            with open(self.filename, 'rb') as f:
                binary_data = f.read()
            
            data = self._deserialize_data(binary_data)
            print(f"RDB snapshot loaded from {self.filename}")
            return data
            
        except Exception as e:
            print(f"Error loading RDB snapshot: {e}")
            return None
    
    def _extract_data_store_state(self, data_store) -> Dict[str, Any]:
        """Extract current state from data store"""
        state = {
            'keys': {},
            'metadata': {
                'created_time': time.time(),
                'key_count': 0
            }
        }
        
        # Extract all valid keys
        for key in data_store.keys():
            value = data_store.get(key)
            if value is not None:
                ttl = data_store.ttl(key)
                data_type = data_store.get_type(key)
                
                state['keys'][key] = {
                    'value': value,
                    'type': data_type,
                    'ttl': ttl if ttl > 0 else None,
                    'expiry_time': time.time() + ttl if ttl > 0 else None
                }
        
        state['metadata']['key_count'] = len(state['keys'])
        return state
    
    def _serialize_data(self, data: Dict[str, Any]) -> bytes:
        """
        Serialize data store to binary format
        
        Args:
            data: Data store state to serialize
            
        Returns:
            Binary representation of data
        """
        try:
            # Create RDB header: MAGIC_STRING = b'REDIS' + VERSION = b'0001'
            header = self.MAGIC_STRING + self.VERSION
            
            # Serialize data using pickle
            serialized_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Compress if enabled
            if self.compression:
                serialized_data = gzip.compress(serialized_data)
            
            # Add checksum if enabled
            if self.checksum:
                checksum = hashlib.md5(serialized_data).digest()
                result = header + checksum + serialized_data
            else:
                result = header + serialized_data
            
            return result
            
        except Exception as e:
            print(f"Error serializing data: {e}")
            raise
    
    def _deserialize_data(self, binary_data: bytes) -> Dict[str, Any]:
        """
        Deserialize binary data to data store format
        
        Args:
            binary_data: Binary data to deserialize
            
        Returns:
            Deserialized data dictionary
        """
        try:
            # Check magic string and version
            if not binary_data.startswith(self.MAGIC_STRING + self.VERSION):
                raise ValueError("Invalid RDB file format")
            
            offset = len(self.MAGIC_STRING + self.VERSION)
            
            # Extract checksum if enabled
            if self.checksum:
                checksum = binary_data[offset:offset + 16]  # MD5 is 16 bytes
                offset += 16
                
                # Verify checksum
                data_to_verify = binary_data[offset:]
                expected_checksum = hashlib.md5(data_to_verify).digest()
                if checksum != expected_checksum:
                    raise ValueError("RDB checksum verification failed")
            
            # Extract serialized data
            serialized_data = binary_data[offset:]
            
            # Decompress if needed
            if self.compression:
                try:
                    serialized_data = gzip.decompress(serialized_data)
                except gzip.BadGzipFile:
                    # Try without compression for backward compatibility
                    pass
            
            # Deserialize data
            data = pickle.loads(serialized_data)
            return data
            
        except Exception as e:
            print(f"Error deserializing data: {e}")
            raise
    
    def get_last_save_time(self) -> int:
        """Get timestamp of last successful save"""
        return int(self.last_save_time)
    
    def file_exists(self) -> bool:
        """Check if RDB file exists"""
        return os.path.exists(self.filename)
    
    def get_file_size(self) -> int:
        """Get RDB file size"""
        try:
            return os.path.getsize(self.filename)
        except OSError:
            return 0
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the RDB file"""
        if not self.file_exists():
            return {'exists': False}
        
        try:
            stat = os.stat(self.filename)
            return {
                'exists': True,
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'last_save_time': self.last_save_time
            }
        except OSError:
            return {'exists': False}
