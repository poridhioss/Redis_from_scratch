"""
Data Recovery Management

Handles loading data from AOF files on server startup.
"""

import os
import time
from typing import Optional, Dict
from .aof import AOFWriter


class RecoveryManager:
    """Manages data recovery from AOF files"""
    
    def __init__(self, aof_filename: str):
        """
        Initialize recovery manager
        
        Args:
            aof_filename: Path to AOF file
        """
        self.aof_filename = aof_filename
        self.aof_handler = None
    
    def recover_data(self, data_store, command_handler=None) -> bool:
        """
        Recover data from AOF file
        
        Args:
            data_store: Data store to populate
            command_handler: Command handler for AOF replay (optional)
            
        Returns:
            True if data was successfully recovered
        """
        try:
            # Check if AOF file exists
            aof_exists = os.path.exists(self.aof_filename)
            
            if not aof_exists:
                print("No AOF file found, starting with empty database")
                return True
            
            print(f"Loading data from AOF file: {self.aof_filename}")
            return self._replay_aof(data_store, command_handler)
            
        except Exception as e:
            print(f"Error during data recovery: {e}")
            return self._handle_corruption(e)
    
    def _replay_aof(self, data_store, command_handler) -> bool:
        """
        Replay commands from AOF file
        
        Args:
            data_store: Data store to populate
            command_handler: Command handler to execute commands
            
        Returns:
            True if successful
        """
        try:
            commands_replayed = 0
            
            with open(self.aof_filename, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse command from AOF format: "timestamp COMMAND args..."
                        parts = line.split(' ', 2)
                        if len(parts) < 2:
                            continue
                        
                        timestamp = parts[0]  # We can use this for validation
                        command = parts[1].upper()
                        args = parts[2].split() if len(parts) > 2 else []
                        
                        # Execute command directly on data store
                        self._execute_recovery_command(data_store, command, args)
                        commands_replayed += 1
                        
                    except Exception as e:
                        print(f"Error replaying command at line {line_num}: {e}")
                        print(f"Problematic line: {line}")
                        # Continue with next command
                        continue
            
            print(f"Replayed {commands_replayed} commands from AOF")
            return True
            
        except Exception as e:
            print(f"Error replaying AOF file: {e}")
            return False
    
    def _execute_recovery_command(self, data_store, command: str, args: list) -> None:
        """
        Execute a single recovery command on the data store
        
        Args:
            data_store: Data store to execute command on
            command: Command to execute
            args: Command arguments
        """
        try:
            if command == 'SET':
                if len(args) >= 2:
                    key = args[0]
                    value = ' '.join(args[1:])
                    data_store.set(key, value)
            
            elif command == 'DEL':
                if args:
                    data_store.delete(*args)
            
            elif command == 'EXPIRE':
                if len(args) == 2:
                    key = args[0]
                    seconds = int(args[1])
                    data_store.expire(key, seconds)
            
            elif command == 'EXPIREAT':
                if len(args) == 2:
                    key = args[0]
                    timestamp = int(args[1])
                    data_store.expire_at(key, timestamp)
            
            elif command == 'PERSIST':
                if len(args) == 1:
                    key = args[0]
                    data_store.persist(key)
            
            elif command == 'FLUSHALL':
                data_store.flush()
            
            else:
                # Unknown command - ignore during recovery
                pass
                
        except Exception as e:
            print(f"Error executing recovery command {command}: {e}")
    
    def _handle_corruption(self, error) -> bool:
        """
        Handle corrupted persistence files
        
        Args:
            error: The error that occurred
            
        Returns:
            True if recovery should continue with empty database
        """
        print(f"Persistence file corruption detected: {error}")
        print("Starting with empty database. Consider restoring from backup.")
        
        # In production, you might want to:
        # 1. Create backup of corrupted files
        # 2. Attempt partial recovery
        # 3. Send alerts to administrators
        
        return True  # Continue with empty database
    
    def validate_files(self) -> Dict[str, bool]:
        """
        Validate AOF file without loading it
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'aof_exists': os.path.exists(self.aof_filename),
            'aof_valid': False
        }
        
        # Validate AOF file
        if results['aof_exists']:
            try:
                with open(self.aof_filename, 'r', encoding='utf-8') as f:
                    # Try to read first few lines
                    for i, line in enumerate(f):
                        if i >= 5:  # Check first 5 lines
                            break
                        # Basic format validation
                        parts = line.strip().split(' ', 2)
                        if len(parts) >= 2:
                            try:
                                int(parts[0])  # timestamp should be integer
                            except ValueError:
                                break
                    else:
                        results['aof_valid'] = True
            except Exception:
                results['aof_valid'] = False
        
        return results
