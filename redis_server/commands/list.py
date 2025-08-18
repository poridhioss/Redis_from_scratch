from .base import BaseCommandHandler
from ..response import *

class ListCommands(BaseCommandHandler):
    """Redis List commands: LPUSH, RPUSH, LPOP, RPOP, LRANGE, LLEN, LINDEX, LSET"""
    
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
            
            # Handle negative indices
            if start < 0:
                start = max(0, list_len + start)
            if stop < 0:
                stop = list_len + stop
            
            # Clamp to valid range
            start = max(0, start)
            stop = min(list_len - 1, stop)
            
            if start > stop or start >= list_len:
                return array([])
            
            # Convert deque to list for slicing
            list_items = list(lst)
            result = list_items[start:stop + 1]
            
            return array([bulk_string(item) for item in result])
        except TypeError as e:
            return error(str(e))

    def llen(self, *args):
        """Get length of list"""
        if len(args) != 1:
            return error("wrong number of arguments for 'llen' command")
        
        key = args[0]
        
        if not self.storage._is_key_valid(key):
            return integer(0)
        
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