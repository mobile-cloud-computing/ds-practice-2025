import threading


class StateMachine:
    def __init__(self):
        self.data_store = {}
        self.lock = threading.Lock()

    def apply(self, operation, key, value=None):
        with self.lock:
            if operation == 'set' or operation == 'update':
                return self.set(key, value)
            elif operation == 'get':
                return self.get(key)
            elif operation == 'delete':
                return self.delete(key)
            else:
                return "Unknown operation"

    def set(self, key, value):
        self.data_store[key] = value
        return f"Set {key} = {value}"

    def get(self, key):
        return self.data_store.get(key, "Key not found")

    def delete(self, key):
        if key in self.data_store:
            del self.data_store[key]
            return f"Deleted {key}"
        else:
            return "Key not found"

    def __len__(self):
        """Returns the number of items in the state machine."""
        return len(self.data_store)

    def __repr__(self):
        """Provides a string representation of the state machine."""
        return f"StateMachine with {len(self)} items: {self.data_store}"
