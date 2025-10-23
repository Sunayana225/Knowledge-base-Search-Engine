"""
Repository pattern implementation for database operations.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.models import DocumentModel, DocumentChunkModel
from src.models.document import DocumentMetadata, DocumentChunk, ProcessedDocument, ProcessingStatus
from src.database.connection import db_manager
from src.utils.exceptions import DocumentProcessingError
import pickle


class DocumentRepository:
    """Repository for document metadata operations."""
    
    def __init__(self):
        """Initialize document repository."""
        self.db_manager = db_manager
    
    def create_document(self, metadata: DocumentMetadata) -> DocumentMetadata:
        """
        Create a new document record.
        
        Args:
            metadata: Document metadata
            
        Returns:
            DocumentMetadata: Created document metadata
            
        Raises:
            DocumentProcessingError: If creation fails
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = DocumentModel(
                    id=metadata.id,
                    filename=metadata.filename,
                    file_type=metadata.file_type,
                    upload_date=metadata.upload_date,
                    processing_status=metadata.processing_status,
                    chunk_count=metadata.chunk_count,
                    file_size=metadata.file_size
                )
                session.add(db_document)
                session.flush()  # Ensure ID is generated
                
                return self._model_to_metadata(db_document)
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to create document: {str(e)}")
    
    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """
        Get document metadata by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            DocumentMetadata or None: Document metadata if found
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = session.query(DocumentModel).filter(
                    DocumentModel.id == document_id
                ).first()
                
                if db_document:
                    return self._model_to_metadata(db_document)
                return None
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to get document: {str(e)}")
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[DocumentMetadata]:
        """
        List all documents with pagination.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List[DocumentMetadata]: List of document metadata
        """
        try:
            with self.db_manager.get_session() as session:
                db_documents = session.query(DocumentModel).offset(offset).limit(limit).all()
                
                return [self._model_to_metadata(doc) for doc in db_documents]
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to list documents: {str(e)}")
    
    def update_document_status(self, document_id: str, status: ProcessingStatus, 
                             chunk_count: Optional[int] = None) -> bool:
        """
        Update document processing status.
        
        Args:
            document_id: Document ID
            status: New processing status
            chunk_count: Optional chunk count to update
            
        Returns:
            bool: True if update was successful
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = session.query(DocumentModel).filter(
                    DocumentModel.id == document_id
                ).first()
                
                if db_document:
                    db_document.processing_status = status
                    if chunk_count is not None:
                        db_document.chunk_count = chunk_count
                    return True
                return False
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to update document status: {str(e)}")
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks.
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            with self.db_manager.get_session() as session:
                db_document = session.query(DocumentModel).filter(
                    DocumentModel.id == document_id
                ).first()
                
                if db_document:
                    session.delete(db_document)
                    return True
                return False
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to delete document: {str(e)}")
    
    def _model_to_metadata(self, db_document: DocumentModel) -> DocumentMetadata:
        """Convert database model to metadata object."""
        return DocumentMetadata(
            id=db_document.id,
            filename=db_document.filename,
            file_type=db_document.file_type,
            upload_date=db_document.upload_date,
            processing_status=db_document.processing_status,
            chunk_count=db_document.chunk_count,
            file_size=db_document.file_size
        )


class DocumentChunkRepository:
    """Repository for document chunk operations."""
    
    def __init__(self):
        """Initialize chunk repository."""
        self.db_manager = db_manager
    
    def create_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Create multiple document chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List[DocumentChunk]: Created chunks
        """
        try:
            with self.db_manager.get_session() as session:
                db_chunks = []
                for chunk in chunks:
                    embedding_data = None
                    if chunk.embedding:
                        embedding_data = pickle.dumps(chunk.embedding)
                    
                    db_chunk = DocumentChunkModel(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        chunk_index=chunk.chunk_index,
                        start_position=chunk.start_position,
                        end_position=chunk.end_position,
                        embedding_vector=embedding_data
                    )
                    db_chunks.append(db_chunk)
                    session.add(db_chunk)
                
                session.flush()
                return [self._model_to_chunk(db_chunk) for db_chunk in db_chunks]
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to create chunks: {str(e)}")
    
    def get_chunks_by_document(self, document_id: str) -> List[DocumentChunk]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        try:
            with self.db_manager.get_session() as session:
                db_chunks = session.query(DocumentChunkModel).filter(
                    DocumentChunkModel.document_id == document_id
                ).order_by(DocumentChunkModel.chunk_index).all()
                
                return [self._model_to_chunk(chunk) for chunk in db_chunks]
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to get chunks: {str(e)}")
    
    def update_chunk_embedding(self, chunk_id: str, embedding: List[float]) -> bool:
        """
        Update chunk embedding.
        
        Args:
            chunk_id: Chunk ID
            embedding: Embedding vector
            
        Returns:
            bool: True if update was successful
        """
        try:
            with self.db_manager.get_session() as session:
                db_chunk = session.query(DocumentChunkModel).filter(
                    DocumentChunkModel.id == chunk_id
                ).first()
                
                if db_chunk:
                    db_chunk.embedding_vector = pickle.dumps(embedding)
                    return True
                return False
                
        except Exception as e:
            raise DocumentProcessingError(f"Failed to update chunk embedding: {str(e)}")
    
    def _model_to_chunk(self, db_chunk: DocumentChunkModel) -> DocumentChunk:
        """Convert database model to chunk object."""
        embedding = None
        if db_chunk.embedding_vector:
            embedding = pickle.loads(db_chunk.embedding_vector)
        
        return DocumentChunk(
            id=db_chunk.id,
            document_id=db_chunk.document_id,
            content=db_chunk.content,
            chunk_index=db_chunk.chunk_index,
            start_position=db_chunk.start_position,
            end_position=db_chunk.end_position,
            embedding=embedding
        )