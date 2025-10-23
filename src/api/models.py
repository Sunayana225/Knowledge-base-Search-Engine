"""
Pydantic models for API request/response schemas.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DocumentResponse(BaseModel):
    """Response model for document metadata."""
    id: str
    filename: str
    file_type: str
    upload_date: datetime
    processing_status: str
    chunk_count: int
    file_size: int


class DocumentListResponse(BaseModel):
    """Response model for document list."""
    documents: List[DocumentResponse]
    total: int
    limit: int
    offset: int


class SearchRequest(BaseModel):
    """Request model for search queries."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional list of document IDs to search within")


class CitationResponse(BaseModel):
    """Response model for citations."""
    document_id: str
    filename: str
    content: str
    relevance_score: float


class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str
    answer: str
    sources: List[DocumentResponse]
    citations: List[Dict[str, Any]]
    processing_time: float


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    components: Dict[str, Any]


class UploadResponse(BaseModel):
    """Response model for file upload."""
    message: str
    document_id: str
    filename: str
    processing_status: str