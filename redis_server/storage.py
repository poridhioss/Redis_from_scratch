class DataStore:
    def __init__(self):
        self._data = {}

    def set(self, key, value):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count

    def exists(self, *keys):
        return sum(1 for key in keys if key in self._data)

    def keys(self):
        return list(self._data.keys())

    def flush(self):
        self._data.clear()