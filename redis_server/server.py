import socket
import select
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
                read, _, _ = select.select(
                    [self.server_socket] + list(self.clients.keys()),
                    [], [], 1.0
                )
                
                for sock in read:
                    if sock is self.server_socket:
                        self._accept_client()
                    else:
                        self._handle_client(sock)
                        
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Event loop error: {e}")

    def _accept_client(self):
        client, addr = self.server_socket.accept()
        client.setblocking(False)
        self.clients[client] = {"addr": addr, "buffer": b""}
        client.send(b"+OK\r\n")

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

    def _process_buffer(self, client):
        buffer = self.clients[client]["buffer"]
        
        while b"\r\n" in buffer:
            command, buffer = buffer.split(b"\r\n", 1)
            if command:
                response = self._process_command(command.decode())
                client.send(response)
        
        self.clients[client]["buffer"] = buffer

    def _process_command(self, command_line):
        parts = command_line.strip().split()
        if not parts:
            return error("empty command")
        return self.command_handler.execute(parts[0], *parts[1:])

    def _disconnect_client(self, client):
        client.close()
        self.clients.pop(client, None)

    def stop(self):
        self.running = False
        for client in list(self.clients.keys()):
            self._disconnect_client(client)
        if self.server_socket:
            self.server_socket.close()