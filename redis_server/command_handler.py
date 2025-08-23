from .commands import (
    BasicCommands, ExpirationCommands, ListCommands, 
    HashCommands, SetCommands, PersistenceCommands, InfoCommands, PubSubCommands
)
from .response import error

class CommandHandler:
    def __init__(self, storage, persistence_manager=None, pubsub_manager=None):
        self.storage = storage
        self.persistence_manager = persistence_manager
        self.pubsub_manager = pubsub_manager
        self.command_count = 0
        self.current_client = None  # Track current client for pub/sub commands
        
        # Initialize command handlers
        self.basic_commands = BasicCommands(storage, persistence_manager)
        self.expiration_commands = ExpirationCommands(storage, persistence_manager)
        self.list_commands = ListCommands(storage, persistence_manager)
        self.hash_commands = HashCommands(storage, persistence_manager)
        self.set_commands = SetCommands(storage, persistence_manager)
        self.persistence_commands = PersistenceCommands(storage, persistence_manager)
        self.info_commands = InfoCommands(storage, persistence_manager, self.command_count)
        self.pubsub_commands = PubSubCommands(storage, persistence_manager, pubsub_manager)
        
        # Command registry mapping commands to their handlers
        self.commands = {
            # Basic commands
            "PING": self.basic_commands.ping,
            "ECHO": self.basic_commands.echo,
            "SET": self.basic_commands.set,
            "GET": self.basic_commands.get,
            "DEL": self.basic_commands.delete,
            "EXISTS": self.basic_commands.exists,
            "KEYS": self.basic_commands.keys,
            "FLUSHALL": self.basic_commands.flushall,
            
            # Expiration commands
            "EXPIRE": self.expiration_commands.expire,
            "EXPIREAT": self.expiration_commands.expireat,
            "TTL": self.expiration_commands.ttl,
            "PTTL": self.expiration_commands.pttl,
            "PERSIST": self.expiration_commands.persist,
            "TYPE": self.expiration_commands.get_type,
            
            # List commands
            "LPUSH": self.list_commands.lpush,
            "RPUSH": self.list_commands.rpush,
            "LPOP": self.list_commands.lpop,
            "RPOP": self.list_commands.rpop,
            "LRANGE": self.list_commands.lrange,
            "LLEN": self.list_commands.llen,
            "LINDEX": self.list_commands.lindex,
            "LSET": self.list_commands.lset,
            
            # Hash commands
            "HSET": self.hash_commands.hset,
            "HGET": self.hash_commands.hget,
            "HMSET": self.hash_commands.hmset,
            "HMGET": self.hash_commands.hmget,
            "HGETALL": self.hash_commands.hgetall,
            "HDEL": self.hash_commands.hdel,
            "HEXISTS": self.hash_commands.hexists,
            "HLEN": self.hash_commands.hlen,
            
            # Set commands
            "SADD": self.set_commands.sadd,
            "SREM": self.set_commands.srem,
            "SMEMBERS": self.set_commands.smembers,
            "SISMEMBER": self.set_commands.sismember,
            "SCARD": self.set_commands.scard,
            "SINTER": self.set_commands.sinter,
            "SUNION": self.set_commands.sunion,
            "SDIFF": self.set_commands.sdiff,
            "SINTERSTORE": self.set_commands.sinterstore,
            
            # Persistence commands
            "SAVE": self.persistence_commands.save,
            "BGSAVE": self.persistence_commands.bgsave,
            "BGREWRITEAOF": self.persistence_commands.bgrewriteaof,
            "LASTSAVE": self.persistence_commands.lastsave,
            "CONFIG": self.persistence_commands.config_command,
            "DEBUG": self.persistence_commands.debug_command,
            
            # Info commands
            "INFO": self.info_commands.info,
            
            # Pub/Sub commands
            "SUBSCRIBE": self.pubsub_commands.subscribe,
            "UNSUBSCRIBE": self.pubsub_commands.unsubscribe, 
            "PUBLISH": self.pubsub_commands.publish,
            "PUBSUB": self.pubsub_commands.pubsub,
        }

    def execute(self, command, *args, client=None):
        self.command_count += 1
        
        # Set current client context for pub/sub commands
        if client is not None:
            self.current_client = client
            self.pubsub_commands.set_current_client(client)
        
        # Update command count in info handler
        self.info_commands.update_command_count(self.command_count)
        
        cmd = self.commands.get(command.upper())
        if cmd:
            result = cmd(*args)
            
            # Log write commands to AOF using the base class method
            if self.persistence_manager and self.basic_commands._is_write_command(command):
                self.persistence_manager.log_write_command(command, *args)
            
            return result
        return error(f"Unknown command '{command}'")