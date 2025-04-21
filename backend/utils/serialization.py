"""
Utilities for JSON serialization
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Union
import numpy as np

def serialize_for_json(obj: Any) -> Any:
    """
    Convierte todos los tipos no serializables a JSON en tipos serializables
    
    Args:
        obj: Objeto a serializar
        
    Returns:
        Objeto serializable a JSON
    """
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in list(obj)]
    elif isinstance(obj, (uuid.UUID, datetime)):
        return str(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, "__dict__"):  # Para objetos personalizados
        return serialize_for_json(obj.__dict__)
    else:
        return obj
