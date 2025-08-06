from .storage import KeyValueStorage
from .constants import *

class CommandHandler:
    def __init__(self, storage: KeyValueStorage):
        self.storage = storage
    
    def handle_command(self, command_line: str) -> str:
        """Process a command line and return response"""
        parts = command_line.split()
        if not parts:
            return "-ERR empty command\r\n"
        
        command = parts[0].upper()
        args = parts[1:]

        print(f"Received command: {command} with args: {args}")
        
        try:
            if command == "SET":
                return self._handle_set(args)
            elif command == "GET":
                return self._handle_get(args)
            elif command == "PING":
                return PONG
            elif command == "ECHO":
                return f"+{' '.join(args)}\r\n" if args else "+\r\n"
            else:
                return f"{UNKNOWN_CMD_ERR} '{command}'\r\n"
        except Exception as e:
            return f"-ERR {str(e)}\r\n"
    
    def _handle_set(self, args) -> str:
        """Handle SET command"""
        if len(args) < 2:
            return f"{WRONG_ARGS_ERR} for 'set' command\r\n"
        
        key, value = args[0], ' '.join(args[1:])
        self.storage.set(key, value)
        return OK
    
    def _handle_get(self, args) -> str:
        """Handle GET command"""
        if len(args) != 1:
            return f"{WRONG_ARGS_ERR} for 'get' command\r\n"
        
        value = self.storage.get(args[0])
        return NULL_BULK_STRING if value is None else f"${len(value)}\r\n{value}\r\n"