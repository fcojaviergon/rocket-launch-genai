from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class UserRegisteredEvent:
    """Event emitted when a user registers"""
    user_id: str
    email: str
    name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: str = "auth.user_registered"
