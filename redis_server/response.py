def ok():
    return b"+OK\r\n"

def pong():
    return b"+PONG\r\n"

def null_bulk_string():
    return b"$-1\r\n"

def simple_string(value):
    return f"+{value}\r\n".encode()

def bulk_string(value):
    if value is None:
        return null_bulk_string()
    return f"${len(value)}\r\n{value}\r\n".encode()

def error(message):
    return f"-ERR {message}\r\n".encode()

def integer(value):
    return f":{value}\r\n".encode()

def array(items):
    if not items:
        return b"*0\r\n"
    result = [f"*{len(items)}\r\n".encode()]
    result.extend(items)
    return b"".join(result)