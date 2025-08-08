import time
from .storage import DataStore
from .response import *

class CommandHandler:
    def __init__(self, storage):
        self.storage = storage
        self.command_count = 0
        self.commands = {
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
            "TYPE": self.get_type
        }

    def execute(self, command, *args):
        self.command_count += 1
        cmd = self.commands.get(command.upper())
        if cmd:
            return cmd(*args)
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

    def get(self, *args):
        if len(args) != 1:
            return error("wrong number of arguments for 'get' command")
        return bulk_string(self.storage.get(args[0])) # def get(self, key) -> value -> [len(value) {value}]

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