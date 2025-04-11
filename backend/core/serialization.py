import json
import uuid
from datetime import datetime

class UUIDEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle UUID and datetime objects."""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Convert UUID objects to strings
            return str(obj)
        if isinstance(obj, datetime):
            # Convert datetime objects to ISO format strings
            return obj.isoformat()
        # Let the base class handle anything else
        return super().default(obj)

def dumps_with_uuids(obj, **kwargs):
    """
    Wrapper function for json.dumps that uses UUIDEncoder.
    Use this instead of json.dumps when working with UUIDs.
    """
    return json.dumps(obj, cls=UUIDEncoder, **kwargs) 