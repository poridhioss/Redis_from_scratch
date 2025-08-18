from .base import BaseCommandHandler
from ..response import *

class PersistenceCommands(BaseCommandHandler):
    """Persistence commands: SAVE, BGSAVE, BGREWRITEAOF, LASTSAVE, CONFIG, DEBUG"""
    
    def save(self, *args):
        """Synchronous RDB save"""
        if not self.persistence_manager:
            return error("persistence not enabled")
        
        try:
            success = self.persistence_manager.create_rdb_snapshot(self.storage)
            if success:
                return ok()
            else:
                return error("save failed")
        except Exception as e:
            return error(f"save error: {e}")
    
    def bgsave(self, *args):
        """Background RDB save"""
        if not self.persistence_manager:
            return error("persistence not enabled")
        
        try:
            success = self.persistence_manager.create_rdb_snapshot_background(self.storage)
            if success:
                return simple_string("Background saving started")
            else:
                return error("background save failed to start")
        except Exception as e:
            return error(f"bgsave error: {e}")
    
    def bgrewriteaof(self, *args):
        """Background AOF rewrite"""
        if not self.persistence_manager:
            return error("persistence not enabled")
        
        try:
            success = self.persistence_manager.rewrite_aof_background(self.storage)
            if success:
                return simple_string("Background AOF rewrite started")
            else:
                return error("background AOF rewrite failed to start")
        except Exception as e:
            return error(f"bgrewriteaof error: {e}")
    
    def lastsave(self, *args):
        """Get timestamp of last successful save"""
        if not self.persistence_manager:
            return integer(0)
        
        try:
            timestamp = self.persistence_manager.get_last_save_time()
            return integer(timestamp)
        except Exception as e:
            return error(f"lastsave error: {e}")
    
    def config_command(self, *args):
        """CONFIG command for persistence settings"""
        if not args:
            return error("wrong number of arguments for 'config' command")
        
        subcommand = args[0].upper()
        
        if subcommand == "GET":
            if len(args) != 2:
                return error("wrong number of arguments for 'config get' command")
            
            parameter = args[1].lower()
            if self.persistence_manager:
                config_value = self.persistence_manager.config.get(parameter)
                if config_value is not None:
                    return array([bulk_string(parameter), bulk_string(str(config_value))])
            
            return array([])
        
        elif subcommand == "SET":
            if len(args) != 3:
                return error("wrong number of arguments for 'config set' command")
            
            parameter = args[1].lower()
            value = args[2]
            
            if self.persistence_manager:
                try:
                    # Convert string values to appropriate types
                    if parameter in ['aof_enabled', 'rdb_enabled', 'persistence_enabled']:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    elif parameter in ['rdb_save_conditions']:
                        return error("rdb_save_conditions cannot be set via CONFIG SET")
                    
                    self.persistence_manager.config.set(parameter, value)
                    return ok()
                except Exception as e:
                    return error(f"config set error: {e}")
            
            return error("persistence not enabled")
        
        else:
            return error(f"unknown CONFIG subcommand '{subcommand}'")
    
    def debug_command(self, *args):
        """DEBUG command for development/testing"""
        if not args:
            return error("wrong number of arguments for 'debug' command")
        
        subcommand = args[0].upper()
        
        if subcommand == "RELOAD":
            if self.persistence_manager:
                try:
                    # Reload data from persistence files
                    success = self.persistence_manager.recover_data(self.storage, self)
                    if success:
                        return ok()
                    else:
                        return error("reload failed")
                except Exception as e:
                    return error(f"reload error: {e}")
            else:
                return error("persistence not enabled")
        
        else:
            return error(f"unknown DEBUG subcommand '{subcommand}'")