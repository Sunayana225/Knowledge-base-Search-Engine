"""
Main FastAPI application for the Knowledge-base Search Engine.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import io
from fastapi.responses import JSONResponse
from src.api.models import (
    DocumentResponse, DocumentListResponse, SearchRequest, SearchResponse,
    ErrorResponse, HealthResponse
)
from src.services.document_ingestion import DocumentIngestionService
from src.services.document_storage import DocumentStorageService
from src.services.query_processor import QueryProcessor
from src.database.connection import db_manager
from src.utils.exceptions import (
    DocumentProcessingError, ValidationError, QueryProcessingError
)
from src.config.settings import config

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge-base Search Engine",
    description="A RAG-based document search and question answering system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize services
document_ingestion = DocumentIngestionService()
document_storage = DocumentStorageService()
query_processor = QueryProcessor()


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    try:
        db_manager.create_tables()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to create database tables: {e}")
        # Continue startup even if database initialization fails


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Knowledge-base Search Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        health_status = document_storage.health_check()
        
        return HealthResponse(
            status="healthy" if health_status["overall"] else "unhealthy",
            components=health_status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.post("/documents", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Args:
        file: Document file (PDF or TXT)
        
    Returns:
        DocumentResponse: Document metadata and processing status
    """
    try:
        # Read file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        
        # Process document
        processed_doc = document_ingestion.process_and_store_document(
            file_stream, file.filename
        )
        
        return DocumentResponse(
            id=processed_doc.metadata.id,
            filename=processed_doc.metadata.filename,
            file_type=processed_doc.metadata.file_type.value,
            upload_date=processed_doc.metadata.upload_date,
            processing_status=processed_doc.metadata.processing_status.value,
            chunk_count=len(processed_doc.chunks),
            file_size=processed_doc.metadata.file_size
        )
        
    except (DocumentProcessingError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(limit: int = 100, offset: int = 0):
    """
    List uploaded documents with pagination.
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        DocumentListResponse: List of document metadata
    """
    try:
        documents = document_storage.list_documents(limit, offset)
        
        document_responses = [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type.value,
                upload_date=doc.upload_date,
                processing_status=doc.processing_status.value,
                chunk_count=doc.chunk_count,
                file_size=doc.file_size
            )
            for doc in documents
        ]
        
        return DocumentListResponse(
            documents=document_responses,
            total=len(document_responses),
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """
    Get document metadata by ID.
    
    Args:
        document_id: Document ID
        
    Returns:
        DocumentResponse: Document metadata
    """
    try:
        document = document_storage.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type.value,
            upload_date=document.upload_date,
            processing_status=document.processing_status.value,
            chunk_count=document.chunk_count,
            file_size=document.file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and all its associated data.
    
    Args:
        document_id: Document ID
        
    Returns:
        dict: Deletion confirmation
    """
    try:
        # Check if document exists
        document = document_storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document
        success = document_storage.delete_document(document_id)
        
        if success:
            return {"message": f"Document {document_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search documents using natural language queries.
    
    Args:
        request: Search request with query and parameters
        
    Returns:
        SearchResponse: Search results with answer and sources
    """
    try:
        # Process query
        result = query_processor.process_query(
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids
        )
        
        return SearchResponse(
            query=result.query,
            answer=result.answer,
            sources=[
                DocumentResponse(
                    id=doc.id,
                    filename=doc.filename,
                    file_type=doc.file_type.value,
                    upload_date=doc.upload_date,
                    processing_status=doc.processing_status.value,
                    chunk_count=doc.chunk_count,
                    file_size=doc.file_size
                )
                for doc in result.sources
            ],
            citations=[
                {
                    "document_id": citation.document_id,
                    "filename": citation.filename,
                    "content": citation.chunk_content,
                    "relevance_score": citation.relevance_score
                }
                for citation in result.citations
            ],
            processing_time=result.processing_time
        )
        
    except (QueryProcessingError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/statistics")
async def get_statistics():
    """
    Get system statistics.
    
    Returns:
        dict: System statistics
    """
    try:
        stats = document_storage.get_storage_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Error handlers
@app.exception_handler(DocumentProcessingError)
async def document_processing_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(QueryProcessingError)
async def query_processing_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.post("/debug-search")
async def debug_search(request: SearchRequest):
    """
    Debug search endpoint to see what's happening in the search process.
    """
    try:
        import time
        start_time = time.time()
        
        # Get similar chunks
        similar_chunks = document_storage.search_similar_chunks(
            query=request.query,
            top_k=request.top_k
        )
        
        # Get document metadata
        document_ids = list(set(chunk.document_id for chunk in similar_chunks))
        document_metadata = []
        for doc_id in document_ids:
            metadata = document_storage.get_document(doc_id)
            if metadata:
                document_metadata.append(metadata)
        
        # Prepare context
        context_parts = []
        for chunk in similar_chunks:
            doc_metadata = document_storage.get_document(chunk.document_id)
            filename = doc_metadata.filename if doc_metadata else "Unknown document"
            context_part = f"[Source: {filename}]\n{chunk.content.strip()}"
            context_parts.append(context_part)
        
        full_context = "\n\n---\n\n".join(context_parts)
        
        processing_time = time.time() - start_time
        
        return {
            "query": request.query,
            "chunks_found": len(similar_chunks),
            "chunks": [
                {
                    "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    "similarity_score": getattr(chunk, 'similarity_score', 0.0),
                    "document_id": chunk.document_id
                }
                for chunk in similar_chunks
            ],
            "context_length": len(full_context),
            "context_preview": full_context[:500] + "..." if len(full_context) > 500 else full_context,
            "processing_time": processing_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug search failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)