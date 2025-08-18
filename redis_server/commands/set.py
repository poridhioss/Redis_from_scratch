from .base import BaseCommandHandler
from ..response import *

class SetCommands(BaseCommandHandler):
    """Redis Set commands: SADD, SREM, SMEMBERS, SISMEMBER, SCARD, SINTER, SUNION, SDIFF, SINTERSTORE"""
    
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
            # Start with first set
            if not self.storage._is_key_valid(keys[0]):
                return array([])
            
            result_set = self.storage.get_or_create_set(keys[0]).copy()
            
            # Intersect with other sets
            for key in keys[1:]:
                if not self.storage._is_key_valid(key):
                    return array([])  # If any set doesn't exist, intersection is empty
                
                other_set = self.storage.get_or_create_set(key)
                result_set &= other_set
            
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
                    result_set |= set_obj
            
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