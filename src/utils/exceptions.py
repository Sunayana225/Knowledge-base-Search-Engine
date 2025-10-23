"""
Custom exceptions for the Knowledge-base Search Engine.
"""


class KnowledgeBaseException(Exception):
    """Base exception for knowledge base operations."""
    pass


class DocumentProcessingError(KnowledgeBaseException):
    """Exception raised during document processing."""
    pass


class TextExtractionError(DocumentProcessingError):
    """Exception raised during text extraction."""
    pass


class ChunkingError(DocumentProcessingError):
    """Exception raised during document chunking."""
    pass


class EmbeddingError(KnowledgeBaseException):
    """Exception raised during embedding generation."""
    pass


class VectorStorageError(KnowledgeBaseException):
    """Exception raised during vector storage operations."""
    pass


class QueryProcessingError(KnowledgeBaseException):
    """Exception raised during query processing."""
    pass


class AnswerSynthesisError(KnowledgeBaseException):
    """Exception raised during answer synthesis."""
    pass


class ValidationError(KnowledgeBaseException):
    """Exception raised during input validation."""
    pass


class FileFormatError(DocumentProcessingError):
    """Exception raised for unsupported file formats."""
    pass


class FileSizeError(DocumentProcessingError):
    """Exception raised when file size exceeds limits."""
    pass