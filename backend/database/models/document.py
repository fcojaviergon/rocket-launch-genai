from sqlalchemy import Column, String, ForeignKey, Text, DateTime, ARRAY, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from database.models.base import BaseModel
import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector

class Document(BaseModel):
    """Model for documents"""
    __tablename__ = "documents"
    
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(String, nullable=True)  # Physical file path
    type = Column(String, nullable=True)  # Document type (pdf, doc, txt, etc)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")
    processing_results = relationship("DocumentProcessingResult", back_populates="document", cascade="all, delete-orphan")
    pipeline_executions = relationship("PipelineExecution", back_populates="document")

class DocumentEmbedding(BaseModel):
    """Model for document embeddings"""
    __tablename__ = "document_embeddings"
    
    document_id = Column(UUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # Dimension for OpenAI embeddings
    chunk_index = Column(Integer, nullable=True)  # For chunk embeddings
    chunk_text = Column(Text, nullable=True)  # Text of the chunk
    
    # Relationships
    document = relationship("Document", back_populates="embeddings")


class DocumentProcessingResult(BaseModel):
    """Model for document processing results"""
    __tablename__ = "document_processing_results"
    
    document_id = Column(UUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    pipeline_name = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    keywords = Column(ARRAY(String), nullable=True)
    token_count = Column(Integer, nullable=True)
    process_metadata = Column(JSON, nullable=True)  # Additional processing data
    
    # Relationships
    document = relationship("Document", back_populates="processing_results")
