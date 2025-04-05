class EventBus:
    """Bus of events central for communication between components"""
    
    def __init__(self):
        self.handlers = {}
        
    async def publish(self, event):
        """Publish an event on the bus"""
        event_type = event.event_type
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                await handler(event)
                
    def subscribe(self, event_type, handler):
        """Subscribe a handler to an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        
    def register_handler(self, event_type):
        """Decorator to register an event handler"""
        def decorator(handler):
            self.subscribe(event_type, handler)
            return handler
        return decorator


# Global instance of the event bus
event_bus = EventBus()
