from .base import BaseCommandHandler
from ..response import *

class HashCommands(BaseCommandHandler):
    """Redis Hash commands: HSET, HGET, HMSET, HMGET, HGETALL, HDEL, HEXISTS, HLEN"""
    
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