# Unified Event System

## Overview

The Unified Event System is a central architecture that combines internal component communication and Redis-based real-time notifications. This system enables flexible and decoupled communication between different application modules, improving code maintainability and extensibility.

## Main Components

### UnifiedEventManager

The `UnifiedEventManager` class in `core/events/manager.py` is the central component that:

1. Manages event subscriptions
2. Publishes internal events between components
3. Publishes real-time events through Redis
4. Maintains compatibility with the previous event system

### Event Types

The system supports two main types of events:

1. **Internal Events**: Used for communication between components within the application
2. **Real-Time Events**: Published through Redis for notifications to clients and other services

## System Usage

### Getting the Event Manager

```python
from core.events import get_event_manager

# Get the event manager instance
event_manager = get_event_manager()
```

### Publishing an Event

```python
# Publish an internal event
await event_manager.publish({
    "event_type": "document_processed",
    "data": {
        "document_id": "123",
        "status": "completed"
    }
})

# Publish a real-time event
await event_manager.publish_realtime(
    channel="pipeline:456",
    event_type="pipeline_progress",
    data={
        "pipeline_id": "456",
        "progress": 75,
        "status": "processing"
    }
)
```

### Subscribing to an Event

```python
# Define an event handler
async def handle_document_processed(event):
    document_id = event["data"]["document_id"]
    print(f"Document {document_id} processed")

# Subscribe to the event
event_manager.subscribe("document_processed", handle_document_processed)
```

## Integration with the Analysis System

The unified event system integrates closely with the new analysis system:

1. Analysis processors publish progress events
2. Asynchronous tasks report their status through events
3. Clients receive real-time updates on analysis progress

### Example: Event Flow in RFP Analysis

1. An RFP analysis pipeline is created
2. A `pipeline_created` event is published
3. Asynchronous document processing begins
4. During processing, `document_processing` and `pipeline_progress` events are published
5. Upon completion, a `pipeline_completed` event is published
6. Clients subscribed to the `pipeline:{pipeline_id}` channel receive all updates

## Advantages of the Unified System

1. **Cleaner code**: A single interface for all types of events
2. **Better testability**: Easy to simulate and test
3. **Flexibility**: Support for different types of events and channels
4. **Scalability**: Enables communication between multiple instances and services
5. **Compatibility**: Maintains support for existing code

## Technical Considerations

- The system uses Redis as a backend for real-time events
- Internal events are processed asynchronously
- A retry mechanism is implemented for critical events
- Event serialization and deserialization are handled automatically
