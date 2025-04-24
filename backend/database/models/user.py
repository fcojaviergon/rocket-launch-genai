from __future__ import annotations # Must be at the top
from sqlalchemy import Boolean, Column, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.models.base import BaseModel
from typing import List, Optional, TYPE_CHECKING # Import TYPE_CHECKING
from database.models.token_usage import TokenUsage

# Import related types only for type checking to avoid circular imports
if TYPE_CHECKING:
    from database.models.document import Document
    from database.models.conversation import Conversation
    from database.models.analysis import AnalysisScenario
    from database.models.task import Task

class User(BaseModel):
    """Model for user"""
    __tablename__ = "users"
    
    # Columns using Mapped syntax
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String, default="user")
    
    # Relationships - using strings to avoid circular imports
    # With annotations import, quotes are usually not needed unless types are truly undefined
    documents: Mapped[List[Document]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List[Conversation]] = relationship(back_populates="user", cascade="all, delete-orphan")
    analysis_scenarios: Mapped[List[AnalysisScenario]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List[Task]] = relationship(back_populates="user")
    token_usage: Mapped[List[TokenUsage]] = relationship(back_populates="user")