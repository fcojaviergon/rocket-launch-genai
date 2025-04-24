"""
Paquete de eventos para la aplicación

Exporta tanto el bus de eventos tradicional como el gestor unificado
"""

from core.events.manager import get_event_manager, event_bus

# Exportar para compatibilidad con código existente
__all__ = ['get_event_manager', 'event_bus']
