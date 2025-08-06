import socket
import threading
from .command_handler import CommandHandler
from .storage import KeyValueStorage

class SimpleTCPServer:
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.storage = KeyValueStorage()
        self.command_handler = CommandHandler(self.storage)
    
    def start(self):
        """Start the TCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"Server starting on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    print(f"New connection from {address}")
                    
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Socket error: {e}")
                    break
                    
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
    
    def _handle_client(self, client_socket, address):
        """Handle individual client connection"""
        buffer = ""
        
        try:
            client_socket.send(b"+OK Server ready\r\n")
            
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Process complete commands (handle pipelining)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        command_line = line.strip()
                        
                        if command_line:
                            response = self.command_handler.handle_command(command_line)
                            client_socket.send(response.encode('utf-8'))
                            
                except socket.timeout:
                    continue
                except socket.error:
                    break
                    
        except Exception as e:
            print(f"Client {address} error: {e}")
        finally:
            client_socket.close()
            print(f"Client {address} disconnected")