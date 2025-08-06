from simple_tcp_server import SimpleTCPServer

def main():
    server = SimpleTCPServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()

if __name__ == "__main__":
    main()