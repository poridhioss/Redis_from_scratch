import socket
import select
import time
from .command import CommandHandler
from .storage import DataStore

class RedisServer:
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.clients = {}
        self.storage = DataStore()
        self.command_handler = CommandHandler(self.storage)
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 0.1  # 100ms cleanup interval

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.server_socket.setblocking(False)
        self.running = True
        
        print(f"Redis-style server listening on {self.host}:{self.port}")
        self._event_loop()

    def _event_loop(self):
        while self.running:
            try:
                # Use shorter timeout to enable regular cleanup
                read, _, _ = select.select(
                    [self.server_socket] + list(self.clients.keys()),
                    [], [], 0.05  # 50ms timeout for more responsive cleanup
                )
                
                for sock in read:
                    if sock is self.server_socket: # if sock is the server socket, then accept a new client
                        self._accept_client()
                    else: # if sock is a client socket, then handle the client
                        self._handle_client(sock)
                
                # Perform background cleanup every 100ms
                current_time = time.time()
                if current_time - self.last_cleanup_time >= self.cleanup_interval:
                    self._background_cleanup()
                    self.last_cleanup_time = current_time
                        
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Event loop error: {e}")

    def _accept_client(self):
        try:
            client, addr = self.server_socket.accept()
            client.setblocking(False)
            self.clients[client] = {"addr": addr, "buffer": b""}
            print(f"Client connected from {addr}")
        except Exception as e:
            print(f"Error accepting client: {e}")

    def _handle_client(self, client):
        try:
            data = client.recv(4096)
            if not data:
                self._disconnect_client(client)
                return
                
            self.clients[client]["buffer"] += data
            self._process_buffer(client)
            
        except ConnectionError:
            self._disconnect_client(client)
        except Exception as e:
            print(f"Error handling client: {e}")
            self._disconnect_client(client)

    def _process_buffer(self, client):
        buffer = self.clients[client]["buffer"]
        
        while b"\r\n" in buffer:
            command, buffer = buffer.split(b"\r\n", 1)
            if command:
                try:
                    response = self._process_command(command.decode('utf-8'))
                    client.send(response)
                except Exception as e:
                    print(f"Error processing command: {e}")
                    error_response = f"-ERR {str(e)}\r\n".encode()
                    client.send(error_response)
        
        self.clients[client]["buffer"] = buffer

    def _process_command(self, command_line):
        parts = command_line.strip().split()
        if not parts:
            return b"-ERR empty command\r\n"
        return self.command_handler.execute(parts[0], *parts[1:])

    def _background_cleanup(self):
        """Perform background cleanup of expired keys"""
        try:
            expired_count = self.storage.cleanup_expired_keys()
            if expired_count > 0:
                print(f"Cleaned up {expired_count} expired keys")
        except Exception as e:
            print(f"Error during background cleanup: {e}")

    def _disconnect_client(self, client):
        try:
            addr = self.clients.get(client, {}).get("addr", "unknown")
            print(f"Client {addr} disconnected")
            client.close()
            self.clients.pop(client, None)
        except Exception as e:
            print(f"Error disconnecting client: {e}")

    def stop(self):
        self.running = False
        for client in list(self.clients.keys()):
            self._disconnect_client(client)
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")