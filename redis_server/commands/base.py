from abc import ABC
from ..response import *

class BaseCommandHandler(ABC):
    """Base class for all command handlers"""
    
    def __init__(self, storage, persistence_manager=None):
        self.storage = storage
        self.persistence_manager = persistence_manager
    
    def _is_write_command(self, command):
        """Check if command is a write command that should be logged"""
        write_commands = {
            'SET', 'DEL', 'EXPIRE', 'EXPIREAT', 'PERSIST', 'FLUSHALL',
            'LPUSH', 'RPUSH', 'LPOP', 'RPOP', 'LSET',
            'HSET', 'HMSET', 'HDEL',
            'SADD', 'SREM', 'SINTERSTORE'
        }
        return command.upper() in write_commands
    
    def _format_bytes(self, bytes_count):
        """Format bytes in human readable format"""
        for unit in ['B', 'K', 'M', 'G']:
            if bytes_count < 1024:
                return f"{bytes_count:.1f}{unit}"
            bytes_count /= 1024
        return f"{bytes_count:.1f}T"