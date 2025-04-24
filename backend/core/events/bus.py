# Este archivo se mantiene por compatibilidad con código existente
# Redirige al gestor unificado de eventos en manager.py

from core.events.manager import get_event_manager

# Alias para el gestor unificado
event_bus = get_event_manager()
