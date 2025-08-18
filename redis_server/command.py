import time
from collections import deque
from .storage import DataStore
from .response import *

class CommandHandler:
    def __init__(self, storage, persistence_manager=None):
        self.storage = storage
        self.persistence_manager = persistence_manager
        self.command_count = 0
        # Command mapping
        self.commands = {
            # Basic commands
            "PING": self.ping,
            "ECHO": self.echo,
            "SET": self.set,
            "GET": self.get,
            "DEL": self.delete,
            "EXISTS": self.exists,
            "KEYS": self.keys,
            "FLUSHALL": self.flushall,
            "INFO": self.info,
            "EXPIRE": self.expire,
            "EXPIREAT": self.expireat,
            "TTL": self.ttl,
            "PTTL": self.pttl,
            "PERSIST": self.persist,
            "TYPE": self.get_type,
            # List commands
            "LPUSH": self.lpush,
            "RPUSH": self.rpush,
            "LPOP": self.lpop,
            "RPOP": self.rpop,
            "LRANGE": self.lrange,
            "LLEN": self.llen,
            "LINDEX": self.lindex,
            "LSET": self.lset,
            # Hash commands
            "HSET": self.hset,
            "HGET": self.hget,
            "HMSET": self.hmset,
            "HMGET": self.hmget,
            "HGETALL": self.hgetall,
            "HDEL": self.hdel,
            "HEXISTS": self.hexists,
            "HLEN": self.hlen,
            # Set commands
            "SADD": self.sadd,
            "SREM": self.srem,
            "SMEMBERS": self.smembers,
            "SISMEMBER": self.sismember,
            "SCARD": self.scard,
            "SINTER": self.sinter,
            "SUNION": self.sunion,
            "SDIFF": self.sdiff,
            "SINTERSTORE": self.sinterstore,
            # Persistence commands
            "SAVE": self.save,
            "BGSAVE": self.bgsave,
            "BGREWRITEAOF": self.bgrewriteaof,
            "LASTSAVE": self.lastsave,
            "CONFIG": self.config_command,
            "DEBUG": self.debug_command
        }

    def execute(self, command, *args):
        self.command_count += 1
        cmd = self.commands.get(command.upper())
        if cmd:
            result = cmd(*args)
            
            # Log write commands to AOF
            if self.persistence_manager and self._is_write_command(command):
                self.persistence_manager.log_write_command(command, *args)
            
            return result
        return error(f"Unknown command '{command}'")

    def ping(self, *args):
        return pong()

    def echo(self, *args):
        return simple_string(" ".join(args)) if args else simple_string("")

    def set(self, *args):
        if len(args) < 2:
            return error("wrong number of arguments for 'set' command")
        
        key = args[0]
        value = " ".join(args[1:])
        
        # Parse optional EX parameter for expiration
        expiry_time = None
        if len(args) >= 4 and args[-2].upper() == "EX":
            try:
                seconds = int(args[-1])
                expiry_time = time.time() + seconds
                value = " ".join(args[1:-2])
            except ValueError:
                return error("Invalid expire time in set")
        
        self.storage.set(key, value, expiry_time)
        return ok()

    # def get(self, key) -> value -> [len(value) {value}]
    def get(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'get' command")
        return bulk_string(self.storage.get(args[0])) 

    def delete(self, *args):
        if not args:
            return error("wrong number of arguments for 'del' command")
        return integer(self.storage.delete(*args))

    def exists(self, *args):
        if not args:
            return error("wrong number of arguments for 'exists' command")
        return integer(self.storage.exists(*args))

    def keys(self, *args):
        pattern = args[0] if args else "*"
        keys = self.storage.keys(pattern)
        if not keys:
            return array([])
        return array([bulk_string(key) for key in keys])

    def flushall(self, *args):
        self.storage.flush()
        return ok()

    def expire(self, *args):
        if len(args) != 2:
            return error("Wrong number of arguments for 'expire' command")
        
        key = args[0]
        try:
            seconds = int(args[1])
            if seconds <= 0:
                return integer(0)
            success = self.storage.expire(key, seconds)
            return integer(1 if success else 0)
        except ValueError:
            return error("invalid expire time")

    def expireat(self, *args):
        if len(args) != 2:
            return error("wrong number of arguments for 'expireat' command")
        
        key = args[0]
        try:
            timestamp = int(args[1])
            if timestamp <= time.time():
                return integer(0)
            success = self.storage.expire_at(key, timestamp)
            return integer(1 if success else 0)
        except ValueError:
            return error("invalid timestamp")

    def ttl(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'ttl' command")
        
        ttl_value = self.storage.ttl(args[0])

        if ttl_value == -1:
            return simple_string(f"No expiration set for key: {args[0]}")
        elif ttl_value == -2:
            return simple_string(f"Key has expired: {args[0]}")
        # Return TTL as an integer
        return integer(ttl_value)

    def pttl(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'pttl' command")
        
        pttl_value = self.storage.pttl(args[0])
        if pttl_value == "-1":
            return simple_string(f"No expiration set for key: {args[0]}")
        elif pttl_value == "-2":
            return simple_string(f"Key has expired: {args[0]}")
        # Return PTTL as an integer
        return integer(pttl_value)

    def persist(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'persist' command")
        
        success = self.storage.persist(args[0])
        return integer(1 if success else 0)

    def get_type(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'type' command")
        
        data_type = self.storage.get_type(args[0])
        return simple_string(data_type)

    def info(self, *args):
        memory_usage = self.storage.get_memory_usage()
        key_count = len(self.storage.keys())
        
        info = {
            "server": {
                "redis_version": "7.0.0-custom",
                "redis_mode": "standalone",
                "uptime_in_seconds": int(time.time())
            },
            "stats": {
                "total_commands_processed": self.command_count,
                "keyspace_hits": 0,  # Could be implemented with counters
                "keyspace_misses": 0
            },
            "memory": {
                "used_memory": memory_usage,
                "used_memory_human": self._format_bytes(memory_usage)
            },
            "keyspace": {
                "db0": f"keys={key_count},expires=0,avg_ttl=0"
            }
        }
        
        # Add persistence information if available
        if self.persistence_manager:
            persistence_stats = self.persistence_manager.get_stats()
            info["persistence"] = {
                "aof_enabled": int(persistence_stats.get('aof_enabled', False)),
                "rdb_enabled": int(persistence_stats.get('rdb_enabled', False)),
                "rdb_changes_since_last_save": persistence_stats.get('changes_since_save', 0),
                "rdb_last_save_time": persistence_stats.get('last_rdb_save_time', 0),
                "aof_last_sync_time": persistence_stats.get('last_aof_sync_time', 0),
                "aof_filename": persistence_stats.get('aof_filename', ''),
                "rdb_filename": persistence_stats.get('rdb_filename', '')
            }
        
        # Add type statistics
        type_stats = self.storage.get_type_stats()
        info["types"] = {
            "strings": type_stats['string'],
            "lists": type_stats['list'],
            "sets": type_stats['set'],
            "hashes": type_stats['hash']
        }
        
        sections = []
        for section, data in info.items():
            sections.append(f"# {section}")
            sections.extend(f"{k}:{v}" for k, v in data.items())
            sections.append("")  # Empty line between sections
        
        return bulk_string("\r\n".join(sections))

    def _format_bytes(self, bytes_count):
        """Format bytes in human readable format"""
        for unit in ['B', 'K', 'M', 'G']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f}{unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f}T"
    
    def _is_write_command(self, command):
        """Check if command is a write command that should be logged"""
        write_commands = {
            'SET', 'DEL', 'EXPIRE', 'EXPIREAT', 'PERSIST', 'FLUSHALL',
            'LPUSH', 'RPUSH', 'LPOP', 'RPOP', 'LSET',
            'HSET', 'HMSET', 'HDEL',
            'SADD', 'SREM', 'SINTERSTORE'
        }
        return command.upper() in write_commands

    # ===== LIST COMMANDS =====
    def lpush(self, *args):
        """Push elements to the left (head) of the list"""
        if len(args) < 2:
            return error("wrong number of arguments for 'lpush' command")
        
        key = args[0]
        elements = args[1:]
        
        try:
            lst = self.storage.get_or_create_list(key)
            for element in elements:
                lst.appendleft(element)
            return integer(len(lst))
        except TypeError as e:
            return error(str(e))

    def rpush(self, *args):
        """Push elements to the right (tail) of the list"""
        if len(args) < 2:
            return error("wrong number of arguments for 'rpush' command")
        
        key = args[0]
        elements = args[1:]
        
        try:
            lst = self.storage.get_or_create_list(key)
            for element in elements:
                lst.append(element)
            return integer(len(lst))
        except TypeError as e:
            return error(str(e))

    def lpop(self, *args):
        """Pop element from the left (head) of the list"""
        if len(args) != 1:
            return error("wrong number of arguments for 'lpop' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return null_bulk_string()
        
        try:
            lst = self.storage.get_or_create_list(key)
            if not lst:
                return null_bulk_string()
            
            element = lst.popleft()
            
            # Remove key if list becomes empty
            if not lst:
                self.storage.delete(key)
            
            return bulk_string(element)
        except TypeError as e:
            return error(str(e))

    def rpop(self, *args):
        """Pop element from the right (tail) of the list"""
        if len(args) != 1:
            return error("wrong number of arguments for 'rpop' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return null_bulk_string()
        
        try:
            lst = self.storage.get_or_create_list(key)
            if not lst:
                return null_bulk_string()
            
            element = lst.pop()
            
            # Remove key if list becomes empty
            if not lst:
                self.storage.delete(key)
            
            return bulk_string(element)
        except TypeError as e:
            return error(str(e))

    def lrange(self, *args):
        """Get range of elements from list"""
        if len(args) != 3:
            return error("wrong number of arguments for 'lrange' command")
        
        key, start_str, stop_str = args
        
        try:
            start = int(start_str)
            stop = int(stop_str)
        except ValueError:
            return error("value is not an integer or out of range")
        
        if not self.storage._is_key_valid(key):
            return array([])
        
        try:
            lst = self.storage.get_or_create_list(key)
            list_len = len(lst)
            
            # Handle negative indices. If list length = 5 and stop = -1 → becomes 4 (last element).
            if start < 0:
                start = max(0, list_len + start)
            if stop < 0:
                stop = list_len + stop
            
            # Clamp to valid range
            start = max(0, start)
            stop = min(list_len - 1, stop)
            
            # Check invalid ranges
            if start > stop or start >= list_len:
                return array([])
            
            # Convert deque to list for slicing
            list_items = list(lst)
            result = list_items[start:stop + 1]
            
            # Wraps entire list into RESP format and Bulk String
            return array([bulk_string(item) for item in result])
        except TypeError as e:
            return error(str(e))

    def llen(self, *args):
        """Get length of list"""
        if len(args) != 1:
            return error("wrong number of arguments for 'llen' command")
        
        key = args[0]
        
        # Check key validity
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        # Try to get the list and return the length
        try:
            lst = self.storage.get_or_create_list(key)
            return integer(len(lst))
        except TypeError as e:
            return error(str(e))

    def lindex(self, *args):
        """Get element at index"""
        if len(args) != 2:
            return error("wrong number of arguments for 'lindex' command")
        
        key, index_str = args
        
        try:
            index = int(index_str)
        except ValueError:
            return error("value is not an integer or out of range")
        
        if not self.storage._is_key_valid(key):
            return null_bulk_string()
        
        try:
            lst = self.storage.get_or_create_list(key)
            list_len = len(lst)
            
            # Handle negative indices
            if index < 0:
                index = list_len + index
            
            if index < 0 or index >= list_len:
                return null_bulk_string()
            
            # Convert deque to list for indexing
            list_items = list(lst)
            return bulk_string(list_items[index])
        except TypeError as e:
            return error(str(e))

    def lset(self, *args):
        """Set element at index"""
        if len(args) != 3:
            return error("wrong number of arguments for 'lset' command")
        
        key, index_str, value = args
        
        try:
            index = int(index_str)
        except ValueError:
            return error("value is not an integer or out of range")
        
        if not self.storage._is_key_valid(key):
            return error("no such key")
        
        try:
            lst = self.storage.get_or_create_list(key)
            list_len = len(lst)
            
            # Handle negative indices
            if index < 0:
                index = list_len + index
            
            if index < 0 or index >= list_len:
                return error("index out of range")
            
            # Convert to list, modify, then replace
            list_items = list(lst)
            list_items[index] = value
            
            # Clear and repopulate deque
            lst.clear()
            lst.extend(list_items)
            
            return ok()
        except TypeError as e:
            return error(str(e))

    # ===== HASH COMMANDS =====
    def hset(self, *args):
        """Set field in hash"""
        if len(args) < 3 or len(args) % 2 == 0:
            return error("wrong number of arguments for 'hset' command")
        
        key = args[0]
        field_value_pairs = args[1:]
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            new_fields = 0
            
            # Process field-value pairs
            for i in range(0, len(field_value_pairs), 2):
                field = field_value_pairs[i]
                value = field_value_pairs[i + 1]
                
                if field not in hash_obj:
                    new_fields += 1
                hash_obj[field] = value
            
            return integer(new_fields)
        except TypeError as e:
            return error(str(e))

    def hget(self, *args):
        """Get field from hash"""
        if len(args) != 2:
            return error("wrong number of arguments for 'hget' command")
        
        key, field = args
        
        if not self.storage._is_key_valid(key):
            return null_bulk_string()
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            value = hash_obj.get(field)
            return bulk_string(value) if value is not None else null_bulk_string()
        except TypeError as e:
            return error(str(e))

    def hmset(self, *args):
        """Set multiple fields in hash"""
        if len(args) < 3 or len(args) % 2 == 0:
            return error("wrong number of arguments for 'hmset' command")
        
        key = args[0]
        field_value_pairs = args[1:]
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            
            # Process field-value pairs
            for i in range(0, len(field_value_pairs), 2):
                field = field_value_pairs[i]
                value = field_value_pairs[i + 1]
                hash_obj[field] = value
            
            return ok()
        except TypeError as e:
            return error(str(e))

    def hmget(self, *args):
        """Get multiple fields from hash"""
        if len(args) < 2:
            return error("wrong number of arguments for 'hmget' command")
        
        key = args[0]
        fields = args[1:]
        
        if not self.storage._is_key_valid(key):
            return array([null_bulk_string() for _ in fields])
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            results = []
            
            for field in fields:
                value = hash_obj.get(field)
                results.append(bulk_string(value) if value is not None else null_bulk_string())
            
            return array(results)
        except TypeError as e:
            return error(str(e))

    def hgetall(self, *args):
        """Get all fields and values from hash"""
        if len(args) != 1:
            return error("wrong number of arguments for 'hgetall' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return array([])
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            results = []
            
            for field, value in hash_obj.items():
                results.append(bulk_string(field))
                results.append(bulk_string(value))
            
            return array(results)
        except TypeError as e:
            return error(str(e))

    def hdel(self, *args):
        """Delete fields from hash"""
        if len(args) < 2:
            return error("wrong number of arguments for 'hdel' command")
        
        key = args[0]
        fields = args[1:]
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            deleted_count = 0
            
            for field in fields:
                if field in hash_obj:
                    del hash_obj[field]
                    deleted_count += 1
            
            # Remove key if hash becomes empty
            if not hash_obj:
                self.storage.delete(key)
            
            return integer(deleted_count)
        except TypeError as e:
            return error(str(e))

    def hexists(self, *args):
        """Check if field exists in hash"""
        if len(args) != 2:
            return error("wrong number of arguments for 'hexists' command")
        
        key, field = args
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            return integer(1 if field in hash_obj else 0)
        except TypeError as e:
            return error(str(e))

    def hlen(self, *args):
        """Get number of fields in hash"""
        if len(args) != 1:
            return error("wrong number of arguments for 'hlen' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        try:
            hash_obj = self.storage.get_or_create_hash(key)
            return integer(len(hash_obj))
        except TypeError as e:
            return error(str(e))

    # ===== SET COMMANDS =====
    def sadd(self, *args):
        """Add members to set"""
        if len(args) < 2:
            return error("wrong number of arguments for 'sadd' command")
        
        key = args[0]
        members = args[1:]
        
        try:
            set_obj = self.storage.get_or_create_set(key)
            added_count = 0
            
            for member in members:
                if member not in set_obj:
                    set_obj.add(member)
                    added_count += 1
            
            return integer(added_count)
        except TypeError as e:
            return error(str(e))

    def srem(self, *args):
        """Remove members from set"""
        if len(args) < 2:
            return error("wrong number of arguments for 'srem' command")
        
        key = args[0]
        members = args[1:]
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        try:
            set_obj = self.storage.get_or_create_set(key)
            removed_count = 0
            
            for member in members:
                if member in set_obj:
                    set_obj.remove(member)
                    removed_count += 1
            
            # Remove key if set becomes empty
            if not set_obj:
                self.storage.delete(key)
            
            return integer(removed_count)
        except TypeError as e:
            return error(str(e))

    def smembers(self, *args):
        """Get all members of set"""
        if len(args) != 1:
            return error("wrong number of arguments for 'smembers' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return array([])
        
        try:
            set_obj = self.storage.get_or_create_set(key)
            return array([bulk_string(member) for member in set_obj])
        except TypeError as e:
            return error(str(e))

    def sismember(self, *args):
        """Check if member exists in set"""
        if len(args) != 2:
            return error("wrong number of arguments for 'sismember' command")
        
        key, member = args
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        try:
            set_obj = self.storage.get_or_create_set(key)
            return integer(1 if member in set_obj else 0)
        except TypeError as e:
            return error(str(e))

    def scard(self, *args):
        """Get cardinality (size) of set"""
        if len(args) != 1:
            return error("wrong number of arguments for 'scard' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
        try:
            set_obj = self.storage.get_or_create_set(key)
            return integer(len(set_obj))
        except TypeError as e:
            return error(str(e))

    def sinter(self, *args):
        """Get intersection of sets"""
        if len(args) < 1:
            return error("wrong number of arguments for 'sinter' command")
        
        keys = args
        
        try:
            # Start with a copy of the first set.
            if not self.storage._is_key_valid(keys[0]):
                return array([])
            
            result_set = self.storage.get_or_create_set(keys[0]).copy()
            
            # Intersect with other sets
            for key in keys[1:]:
                if not self.storage._is_key_valid(key):
                    return array([])  # If any set doesn't exist, intersection is empty
                
                other_set = self.storage.get_or_create_set(key)
                result_set &= other_set # Intersect (&=)
            
            return array([bulk_string(member) for member in result_set])
        except TypeError as e:
            return error(str(e))

    def sunion(self, *args):
        """Get union of sets"""
        if len(args) < 1:
            return error("wrong number of arguments for 'sunion' command")
        
        keys = args
        result_set = set()
        
        try:
            for key in keys:
                if self.storage._is_key_valid(key):
                    set_obj = self.storage.get_or_create_set(key)
                    result_set |= set_obj # union (|=)
            
            return array([bulk_string(member) for member in result_set])
        except TypeError as e:
            return error(str(e))

    def sdiff(self, *args):
        """Get difference of sets"""
        if len(args) < 1:
            return error("wrong number of arguments for 'sdiff' command")
        
        keys = args
        
        try:
            # Start with first set
            if not self.storage._is_key_valid(keys[0]):
                return array([])
            
            result_set = self.storage.get_or_create_set(keys[0]).copy()
            
            # Subtract other sets
            for key in keys[1:]:
                if self.storage._is_key_valid(key):
                    other_set = self.storage.get_or_create_set(key)
                    result_set -= other_set
            
            return array([bulk_string(member) for member in result_set])
        except TypeError as e:
            return error(str(e))

    def sinterstore(self, *args):
        """Store intersection of sets in destination key"""
        if len(args) < 2:
            return error("wrong number of arguments for 'sinterstore' command")
        
        destination = args[0]
        keys = args[1:]
        
        try:
            # Calculate intersection
            if not self.storage._is_key_valid(keys[0]):
                # If first set doesn't exist, result is empty
                self.storage.delete(destination)
                return integer(0)
            
            result_set = self.storage.get_or_create_set(keys[0]).copy()
            
            for key in keys[1:]:
                if not self.storage._is_key_valid(key):
                    # If any set doesn't exist, intersection is empty
                    self.storage.delete(destination)
                    return integer(0)
                
                other_set = self.storage.get_or_create_set(key)
                result_set &= other_set
            
            # Store result
            if result_set:
                self.storage.set(destination, result_set)
                return integer(len(result_set))
            else:
                self.storage.delete(destination)
                return integer(0)
        except TypeError as e:
            return error(str(e))
    
    # ===== PERSISTENCE COMMANDS =====
    def save(self, *args):
        """Synchronous RDB save"""
        if not self.persistence_manager:
            return error("persistence not enabled")
        
        try:
            success = self.persistence_manager.create_rdb_snapshot(self.storage)
            if success:
                return ok()
            else:
                return error("save failed")
        except Exception as e:
            return error(f"save error: {e}")
    
    def bgsave(self, *args):
        """Background RDB save"""
        if not self.persistence_manager:
            return error("persistence not enabled")
        
        try:
            success = self.persistence_manager.create_rdb_snapshot_background(self.storage)
            if success:
                return simple_string("Background saving started")
            else:
                return error("background save failed to start")
        except Exception as e:
            return error(f"bgsave error: {e}")
    
    def bgrewriteaof(self, *args):
        """Background AOF rewrite"""
        if not self.persistence_manager:
            return error("persistence not enabled")
        
        try:
            success = self.persistence_manager.rewrite_aof_background(self.storage)
            if success:
                return simple_string("Background AOF rewrite started")
            else:
                return error("background AOF rewrite failed to start")
        except Exception as e:
            return error(f"bgrewriteaof error: {e}")
    
    def lastsave(self, *args):
        """Get timestamp of last successful save"""
        if not self.persistence_manager:
            return integer(0)
        
        try:
            timestamp = self.persistence_manager.get_last_save_time()
            return integer(timestamp)
        except Exception as e:
            return error(f"lastsave error: {e}")
    
    def config_command(self, *args):
        """CONFIG command for persistence settings"""
        if not args:
            return error("wrong number of arguments for 'config' command")
        
        subcommand = args[0].upper()
        
        if subcommand == "GET":
            if len(args) != 2:
                return error("wrong number of arguments for 'config get' command")
            
            parameter = args[1].lower()
            if self.persistence_manager:
                config_value = self.persistence_manager.config.get(parameter)
                if config_value is not None:
                    return array([bulk_string(parameter), bulk_string(str(config_value))])
            
            return array([])
        
        elif subcommand == "SET":
            if len(args) != 3:
                return error("wrong number of arguments for 'config set' command")
            
            parameter = args[1].lower()
            value = args[2]
            
            if self.persistence_manager:
                try:
                    # Convert string values to appropriate types
                    if parameter in ['aof_enabled', 'rdb_enabled', 'persistence_enabled']:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    elif parameter in ['rdb_save_conditions']:
                        # This would need more complex parsing
                        return error("rdb_save_conditions cannot be set via CONFIG SET")
                    
                    self.persistence_manager.config.set(parameter, value)
                    return ok()
                except Exception as e:
                    return error(f"config set error: {e}")
            
            return error("persistence not enabled")
        
        else:
            return error(f"unknown CONFIG subcommand '{subcommand}'")
    
    def debug_command(self, *args):
        """DEBUG command for development/testing"""
        if not args:
            return error("wrong number of arguments for 'debug' command")
        
        subcommand = args[0].upper()
        
        if subcommand == "RELOAD":
            if self.persistence_manager:
                try:
                    # Reload data from persistence files
                    success = self.persistence_manager.recover_data(self.storage, self)
                    if success:
                        return ok()
                    else:
                        return error("reload failed")
                except Exception as e:
                    return error(f"reload error: {e}")
            else:
                return error("persistence not enabled")
        
        else:
            return error(f"unknown DEBUG subcommand '{subcommand}'")