from functools import wraps

class Context:
    def __init__(self, id : int, **kwargs):
        self.id = id
        for k, v in kwargs.items():
            setattr(self, k, v)


class ContextManager:
    def __init__(self):
        self.contexts = {}
        self.active_context = None
    
    def init_context(self, id, data : dict):
        self.contexts[id] = Context(id, data=data)
    
    def add_context_wrapper(self, func):
        @wraps(func)
        def set_context(id, *args, **kwargs):
            self.active_context = self.contexts.get(id, None)
            return func(*args, **kwargs)
        return set_context
