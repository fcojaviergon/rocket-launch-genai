"""
Utilities for JSON serialization
"""
import uuid
import inspect
from datetime import datetime
from typing import Any, Dict, List, Union
import numpy as np

def serialize_for_json(obj: Any, _visited_objs=None) -> Any:
    """
    Convierte todos los tipos no serializables a JSON en tipos serializables
    
    Args:
        obj: Objeto a serializar
        _visited_objs: Set interno para evitar recursión infinita
        
    Returns:
        Objeto serializable a JSON
    """
    # Inicializar el conjunto de objetos visitados para evitar recursión infinita
    if _visited_objs is None:
        _visited_objs = set()
    
    # Verificar si el objeto ya ha sido visitado
    obj_id = id(obj)
    if obj_id in _visited_objs:
        return "[Referencia circular]"
    
    # Para objetos básicos que son directamente serializables
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # Agregar este objeto al conjunto de visitados
    _visited_objs.add(obj_id)
    
    try:
        # Manejar tipos específicos
        if isinstance(obj, dict):
            return {k: serialize_for_json(v, _visited_objs) for k, v in obj.items()}
        elif isinstance(obj, list) or isinstance(obj, tuple):
            return [serialize_for_json(item, _visited_objs) for item in obj]
        elif isinstance(obj, (uuid.UUID, datetime)):
            return str(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # Manejar coroutines
        elif inspect.iscoroutine(obj) or inspect.isawaitable(obj):
            return "[Coroutine]"
        # Manejar objetos con __dict__
        elif hasattr(obj, "__dict__"):
            return serialize_for_json(obj.__dict__, _visited_objs)
        # Intentar convertir a string como último recurso
        else:
            try:
                return str(obj)
            except Exception:
                return "[No serializable]"
    finally:
        # Eliminar este objeto del conjunto de visitados al salir
        _visited_objs.remove(obj_id)
