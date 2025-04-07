from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import MetaData
from typing import Any
from sqlalchemy import Column, DateTime, func, UUID
import uuid
from datetime import datetime

# Define custom naming conventions for indexes and constraints
# Recommended for consistency, especially with Alembic auto-generation
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create metadata with the naming convention
metadata_obj = MetaData(naming_convention=convention)

class BaseModel(DeclarativeBase):
    """
    Base class for SQLAlchemy models using DeclarativeBase with type hints.
    Includes default metadata with naming conventions.
    """
    metadata = metadata_obj

    __abstract__ = True
    
    # Define common columns using Mapped and mapped_column
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
