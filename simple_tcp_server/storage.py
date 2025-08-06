class KeyValueStorage:
    def __init__(self):
        self._store = {}
    
    def set(self, key: str, value: str) -> None:
        """Store a key-value pair"""
        self._store[key] = value
    
    def get(self, key: str) -> str:
        """Retrieve a value by key"""
        return self._store.get(key)
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair"""
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    def flush(self) -> None:
        """Clear all data"""
        self._store.clear()