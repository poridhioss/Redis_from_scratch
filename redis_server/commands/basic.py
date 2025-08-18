import time
from .base import BaseCommandHandler
from ..response import *

class BasicCommands(BaseCommandHandler):
    """Basic Redis commands: PING, ECHO, SET, GET, DEL, EXISTS, KEYS, FLUSHALL"""
    
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