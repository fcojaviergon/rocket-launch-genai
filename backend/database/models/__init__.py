from database.models.base import BaseModel
from database.models.document import Document, DocumentEmbedding, DocumentProcessingResult
from database.models.conversation import Conversation, Message
from database.models.user import User
from database.models.pipeline import Pipeline, PipelineExecution

# This ensures that SQLAlchemy loads all models in the correct order
__all__ = [
    "BaseModel",  
    "Document", 
    "DocumentEmbedding", 
    "DocumentProcessingResult", 
    "Conversation", 
    "Message", 
    "User",
    "Pipeline",
    "PipelineExecution"
]
