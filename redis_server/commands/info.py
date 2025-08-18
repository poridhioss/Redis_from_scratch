import time
from .base import BaseCommandHandler
from ..response import *

class InfoCommands(BaseCommandHandler):
    """Info and statistics commands: INFO"""
    
    def __init__(self, storage, persistence_manager=None, command_count=0):
        super().__init__(storage, persistence_manager)
        self.command_count = command_count
    
    def update_command_count(self, count):
        """Update command count from main handler"""
        self.command_count = count
    
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