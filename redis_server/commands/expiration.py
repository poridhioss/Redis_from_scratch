import time
from .base import BaseCommandHandler
from ..response import *

class ExpirationCommands(BaseCommandHandler):
    """Expiration-related commands: EXPIRE, EXPIREAT, TTL, PTTL, PERSIST, TYPE"""
    
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
        return integer(ttl_value)

    def pttl(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'pttl' command")
        
        pttl_value = self.storage.pttl(args[0])
        if pttl_value == "-1":
            return simple_string(f"No expiration set for key: {args[0]}")
        elif pttl_value == "-2":
            return simple_string(f"Key has expired: {args[0]}")
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