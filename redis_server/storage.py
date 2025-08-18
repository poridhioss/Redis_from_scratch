import time
import random
import fnmatch
from collections import deque

class DataStore:
    def __init__(self):
        # Storage format: {key: (value, type, expiry_time)}
        self._data = {}
        self._memory_usage = 0
        # Type statistics for INFO command
        self._type_stats = {
            "string": 0,
            "list": 0,
            "set": 0,
            "hash": 0
        }

    def set(self, key, value, expiry_time=None):
        # Remove old key if exists to update memory usage and type stats
        if key in self._data:
            old_value, old_type, _ = self._data[key]
            self._memory_usage -= self._calculate_memory_usage(key, old_value)
            self._type_stats[old_type] -= 1
        
        data_type = self._get_data_type(value)
        self._data[key] = (value, data_type, expiry_time)
        self._memory_usage += self._calculate_memory_usage(key, value)
        self._type_stats[data_type] += 1

    def get(self, key):
        # check if key exists and hasn't expired
        if not self._is_key_valid(key):
            return None
        value, _, _ = self._data[key] # value, type, expiry_time
        return value

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._data:
                value, data_type, _ = self._data[key] # retrieve the value and type
                self._memory_usage -= self._calculate_memory_usage(key, value) # remove memory usage
                self._type_stats[data_type] -= 1  # Update type statistics
                del self._data[key] # delete the key
                count += 1 # increment count to track deleted keys
        return count

    def exists(self, *keys):
        return sum(1 for key in keys if self._is_key_valid(key))


    """
    Pattern matching for keys: fnmatch.fnmatch for Unix shell-style wildcard matching
    * matches any characters
    ? matches a single character
    [abc] matches any character in the brackets
    """

    def keys(self, pattern="*"):
        valid_keys = [key for key in self._data.keys() if self._is_key_valid(key)]
        if pattern == "*":
            return valid_keys
        return [key for key in valid_keys if fnmatch.fnmatch(key, pattern)]

    def flush(self):
        self._data.clear()
        self._memory_usage = 0
        # Reset type statistics
        self._type_stats = {
            "string": 0,
            "list": 0,
            "set": 0,
            "hash": 0
        }

    def expire(self, key, seconds):
        """Set expiration time in seconds from now"""
        if not self._is_key_valid(key):
            return False
        
        value, data_type, _ = self._data[key]
        expiry_time = time.time() + seconds # calculate future expiration time
        self._data[key] = (value, data_type, expiry_time)
        return True

    def expire_at(self, key, timestamp):
        """Set expiration at specific timestamp"""
        if not self._is_key_valid(key):
            return False
        
        value, data_type, _ = self._data[key]
        self._data[key] = (value, data_type, timestamp)
        return True
 
    def ttl(self, key):
        """Get TTL in seconds"""
        if key not in self._data:
            return -2  # Key doesn't exist
        
        value, data_type, expiry_time = self._data[key]
        if expiry_time is None:
            return -1  # No expiration set
        
        remaining = expiry_time - time.time()
        if remaining <= 0:
            # Key expired, remove it
            self._memory_usage -= self._calculate_memory_usage(key, value)
            self._type_stats[data_type] -= 1
            del self._data[key]
            return -2
        
        return int(remaining)

    def pttl(self, key):
        """Get TTL in milliseconds"""
        if key not in self._data:
            return -2  # Key doesn't exist
        
        value, data_type, expiry_time = self._data[key]
        if expiry_time is None:
            return -1  # No expiration set
        
        remaining = expiry_time - time.time()
        if remaining <= 0:
            # Key expired, remove it
            self._memory_usage -= self._calculate_memory_usage(key, value)
            self._type_stats[data_type] -= 1
            del self._data[key]
            return -2
        
        return int(remaining * 1000)

    def persist(self, key):
        """Remove expiration from key"""
        if not self._is_key_valid(key):
            return False
        
        value, data_type, _ = self._data[key]
        self._data[key] = (value, data_type, None)
        return True

    def get_type(self, key):
        """Get data type of key"""
        if not self._is_key_valid(key):
            return "none"
        
        _, data_type, _ = self._data[key]
        return data_type

    def get_memory_usage(self):
        """Get current memory usage in bytes"""
        return self._memory_usage

    def cleanup_expired_keys(self):
        """Background cleanup of expired keys (probabilistic approach)"""
        if not self._data:
            return 0
        
        current_time = time.time()
        expired_keys = []
        
        # Sample random keys for expiration check
        sample_size = min(20, len(self._data))  # Check up to 20 keys
        sample_keys = random.sample(list(self._data.keys()), sample_size)
        
        for key in sample_keys:
            value, _, expiry_time = self._data[key]
            if expiry_time is not None and expiry_time <= current_time:
                expired_keys.append(key)
        
        # Remove expired keys
        for key in expired_keys:
            value, data_type, _ = self._data[key]
            self._memory_usage -= self._calculate_memory_usage(key, value)
            self._type_stats[data_type] -= 1
            del self._data[key]
        
        return len(expired_keys)

    def get_type_stats(self):
        """Get statistics for each data type"""
        return self._type_stats.copy()

    def check_type(self, key, expected_type):
        """Check if key exists and has the expected type"""
        if not self._is_key_valid(key):
            return False
        
        _, data_type, _ = self._data[key]
        return data_type == expected_type

    def get_or_create_list(self, key):
        """Get existing list or create new one"""
        if not self._is_key_valid(key):
            # Create new list
            new_list = deque()
            self.set(key, new_list)
            return new_list
        
        value, data_type, _ = self._data[key]
        if data_type != "list":
            raise TypeError(f"WRONGTYPE Operation against a key holding the wrong kind of value")
        
        return value

    def get_or_create_hash(self, key):
        """Get existing hash or create new one"""
        if not self._is_key_valid(key):
            # Create new hash
            new_hash = {}
            self.set(key, new_hash)
            return new_hash
        
        value, data_type, _ = self._data[key]
        if data_type != "hash":
            raise TypeError(f"WRONGTYPE Operation against a key holding the wrong kind of value")
        
        return value

    def get_or_create_set(self, key):
        """Get existing set or create new one"""
        if not self._is_key_valid(key):
            # Create new set
            new_set = set()
            self.set(key, new_set)
            return new_set
        
        value, data_type, _ = self._data[key]
        if data_type != "set":
            raise TypeError(f"WRONGTYPE Operation against a key holding the wrong kind of value")
        
        return value

    def _is_key_valid(self, key):
        """Check if key exists and hasn't expired (lazy expiration)"""
        if key not in self._data:
            return False
        
        value, _, expiry_time = self._data[key]
        if expiry_time is not None and expiry_time <= time.time():
            # Key expired, remove it
            value, data_type, _ = self._data[key]
            self._memory_usage -= self._calculate_memory_usage(key, value)
            self._type_stats[data_type] -= 1
            del self._data[key]
            return False
        
        return True

    def _get_data_type(self, value):
        """Determine Redis data type"""
        if isinstance(value, str):
            return "string"
        elif isinstance(value, int):
            return "string"  # Redis stores numbers as strings
        elif isinstance(value, deque):
            return "list"
        elif isinstance(value, list):
            return "list"
        elif isinstance(value, set):
            return "set"
        elif isinstance(value, dict):
            return "hash"
        else:
            return "string"

    def _calculate_memory_usage(self, key, value):
        """Calculate approximate memory usage for a key-value pair"""
        key_size = len(str(key).encode('utf-8'))
        
        if isinstance(value, (deque, list)):
            value_size = sum(len(str(item).encode('utf-8')) for item in value)
        elif isinstance(value, set):
            value_size = sum(len(str(item).encode('utf-8')) for item in value)
        elif isinstance(value, dict):
            value_size = sum(len(str(k).encode('utf-8')) + len(str(v).encode('utf-8')) 
                           for k, v in value.items())
        else:
            value_size = len(str(value).encode('utf-8'))
        
        return key_size + value_size + 64  # Add overhead for metadata