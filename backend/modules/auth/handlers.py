from core.events.bus import event_bus
from modules.auth.events import UserRegisteredEvent
import logging

logger = logging.getLogger(__name__)

@event_bus.register_handler("auth.user_registered")
async def send_welcome_email(event: UserRegisteredEvent):
    """Send welcome email when user registers"""
    try:
        # Here you would integrate with your email service
        # For example: await email_service.send_email()
        logger.info(
            f"Welcome email sent to {event.email} "
            f"User ID: {event.user_id} "
            f"Name: {event.name} "
            f"Registered at: {event.timestamp}"
        )
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}") 