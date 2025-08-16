"""
Data Recovery Management

Handles loading data from RDB persistence files on server startup.
"""

import os
import time
from typing import Optional, Dict
from .rdb import RDBHandler


class RecoveryManager:
    """Manages data recovery from RDB files"""
    
    def __init__(self, rdb_filename: str):
        """
        Initialize recovery manager
        
        Args:
            rdb_filename: Path to RDB file
        """
        self.rdb_filename = rdb_filename
        self.rdb_handler = None
    
    def recover_data(self, data_store) -> bool:
        """
        Recover data from RDB persistence file
        
        Args:
            data_store: Data store to populate
            
        Returns:
            True if data was successfully recovered
        """
        try:
            # Check if RDB file exists
            rdb_exists = os.path.exists(self.rdb_filename)
            
            if not rdb_exists:
                print("No RDB file found, starting with empty database")
                return True
            
            print(f"Loading data from RDB file: {self.rdb_filename}")
            return self._load_from_rdb(data_store)
            
        except Exception as e:
            print(f"Error during data recovery: {e}")
            return self._handle_corruption(e)
    
    def _load_from_rdb(self, data_store) -> bool:
        """
        Load data from RDB file
        
        Args:
            data_store: Data store to populate
            
        Returns:
            True if successful
        """
        try:
            rdb_handler = RDBHandler(self.rdb_filename)
            rdb_data = rdb_handler.load_snapshot()
            
            if rdb_data is None:
                print("No data found in RDB file")
                return False
            
            # Clear existing data
            data_store.flush()
            
            # Load keys from RDB data
            keys_data = rdb_data.get('keys', {})
            current_time = time.time()
            loaded_keys = 0
            
            for key, key_data in keys_data.items():
                value = key_data.get('value')
                expiry_time = key_data.get('expiry_time')
                
                # Skip expired keys
                if expiry_time and expiry_time <= current_time:
                    continue
                
                # Set the key-value pair
                data_store.set(key, value, expiry_time)
                loaded_keys += 1
            
            print(f"Loaded {loaded_keys} keys from RDB file")
            return True
            
        except Exception as e:
            print(f"Error loading RDB file: {e}")
            return False
    
    
    def _handle_corruption(self, error) -> bool:
        """
        Handle corrupted RDB file
        
        Args:
            error: The error that occurred
            
        Returns:
            True if recovery should continue with empty database
        """
        print(f"RDB file corruption detected: {error}")
        print("Starting with empty database. Consider restoring from backup.")
        
        # In production, you might want to:
        # 1. Create backup of corrupted files
        # 2. Attempt partial recovery
        # 3. Send alerts to administrators
        
        return True  # Continue with empty database
    
    def validate_files(self) -> Dict[str, bool]:
        """
        Validate RDB persistence file without loading it
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'rdb_exists': os.path.exists(self.rdb_filename),
            'rdb_valid': False
        }
        
        # Validate RDB file
        if results['rdb_exists']:
            try:
                with open(self.rdb_filename, 'rb') as f:
                    header = f.read(9)  # REDIS + version
                    if header.startswith(b'REDIS'):
                        results['rdb_valid'] = True
            except Exception:
                results['rdb_valid'] = False
        
        return results
