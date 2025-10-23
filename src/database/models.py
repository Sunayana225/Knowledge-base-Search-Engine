"""
SQLAlchemy database models for document storage.
"""
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from src.models.document import ProcessingStatus, FileType

Base = declarative_base()


class DocumentModel(Base):
    """Database model for document metadata."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    upload_date = Column(DateTime, default=func.now(), nullable=False)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Relationship to chunks
    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")


class DocumentChunkModel(Base):
    """Database model for document chunks."""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    embedding_vector = Column(LargeBinary, nullable=True)  # Serialized embedding
    
    # Relationship to document
    document = relationship("DocumentModel", back_populates="chunks")