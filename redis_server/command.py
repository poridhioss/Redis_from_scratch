from .storage import DataStore
from .response import *

class CommandHandler:
    def __init__(self, storage):
        self.storage = storage
        self.commands = {
            "PING": self.ping,
            "ECHO": self.echo,
            "SET": self.set,
            "GET": self.get,
            "DEL": self.delete,
            "EXISTS": self.exists,
            "KEYS": self.keys,
            "FLUSHALL": self.flushall,
            "INFO": self.info
        }

    def execute(self, command, *args): # execute("SET", "mykey", "myvalue"), args = ("mykey", "myvalue")
        cmd = self.commands.get(command.upper()) # get the command function
        if cmd:
            return cmd(*args)
        return error(f"unknown command '{command}'")

    def ping(self, *args):
        return pong()

    def echo(self, *args):
        return simple_string(" ".join(args)) if args else simple_string("")

    def set(self, *args):
        if len(args) < 2:
            return error("wrong number of arguments for 'set' command")
        self.storage.set(args[0], " ".join(args[1:]))
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
        keys = self.storage.keys()
        if not keys:
            return array([])
        return array([bulk_string(key) for key in keys])

    def flushall(self, *args):
        self.storage.flush()
        return ok()

    def info(self, *args):
        info = {
            "server": {
                "redis_version": "7.0.0-custom",
                "redis_mode": "standalone"
            },
            "stats": {
                "total_commands_processed": 0  # Would track this in server
            },
            "keyspace": {
                "db0": f"keys={len(self.storage.keys())},expires=0"
            }
        }
        sections = []
        for section, data in info.items():
            sections.append(f"#{section}")
            sections.extend(f"{k}:{v}" for k, v in data.items())
        return bulk_string("\n".join(sections))