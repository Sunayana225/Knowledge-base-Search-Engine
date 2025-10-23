"""
Document storage and indexing system that coordinates database and vector storage.
"""
from typing import List, Optional
from src.models.document import DocumentMetadata, DocumentChunk, ProcessedDocument, ProcessingStatus
from src.database.repository import DocumentRepository, DocumentChunkRepository
from src.services.vector_storage import VectorStorageFactory
from src.services.embedding_service import EmbeddingService
from src.utils.exceptions import DocumentProcessingError, VectorStorageError, EmbeddingError
from src.config.settings import config


class DocumentStorageService:
    """Service for coordinating document storage across database and vector storage."""
    
    def __init__(self):
        """Initialize document storage service."""
        self.doc_repository = DocumentRepository()
        self.chunk_repository = DocumentChunkRepository()
        self.vector_storage = VectorStorageFactory.create_storage()
        self.embedding_service = EmbeddingService()
    
    def store_processed_document(self, processed_doc: ProcessedDocument) -> str:
        """
        Store a processed document with embeddings in both database and vector storage.
        
        Args:
            processed_doc: Processed document with metadata and chunks
            
        Returns:
            str: Document ID
            
        Raises:
            DocumentProcessingError: If storage fails
        """
        try:
            # Update processing status
            processed_doc.metadata.processing_status = ProcessingStatus.PROCESSING
            
            # Store document metadata in database
            stored_metadata = self.doc_repository.create_document(processed_doc.metadata)
            
            if processed_doc.chunks:
                # Generate embeddings for chunks if not already present
                chunks_with_embeddings = self._ensure_embeddings(processed_doc.chunks)
                
                # Store chunks in database
                stored_chunks = self.chunk_repository.create_chunks(chunks_with_embeddings)
                
                # Store embeddings in vector database
                self.vector_storage.store_embeddings(stored_chunks)
                
                # Update document status to completed
                self.doc_repository.update_document_status(
                    stored_metadata.id,
                    ProcessingStatus.COMPLETED,
                    len(stored_chunks)
                )
            else:
                # No chunks to process
                self.doc_repository.update_document_status(
                    stored_metadata.id,
                    ProcessingStatus.COMPLETED,
                    0
                )
            
            return stored_metadata.id
            
        except (EmbeddingError, VectorStorageError) as e:
            # Update status to failed
            if 'stored_metadata' in locals():
                self.doc_repository.update_document_status(
                    stored_metadata.id,
                    ProcessingStatus.FAILED
                )
            raise DocumentProcessingError(f"Failed to store document: {str(e)}")
        except Exception as e:
            raise DocumentProcessingError(f"Document storage failed: {str(e)}")
    
    def _ensure_embeddings(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Ensure all chunks have embeddings, generating them if necessary.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List[DocumentChunk]: Chunks with embeddings
        """
        chunks_needing_embeddings = []
        chunks_with_embeddings = []
        
        for chunk in chunks:
            if chunk.embedding:
                chunks_with_embeddings.append(chunk)
            else:
                chunks_needing_embeddings.append(chunk)
        
        if chunks_needing_embeddings:
            # Generate embeddings for chunks that don't have them
            texts = [chunk.content for chunk in chunks_needing_embeddings]
            embeddings = self.embedding_service.generate_embeddings(texts)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks_needing_embeddings, embeddings):
                chunk.embedding = embedding
                chunks_with_embeddings.append(chunk)
        
        return chunks_with_embeddings
    
    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """
        Get document metadata by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            DocumentMetadata or None: Document metadata if found
        """
        return self.doc_repository.get_document(document_id)
    
    def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List[DocumentChunk]: Document chunks
        """
        return self.chunk_repository.get_chunks_by_document(document_id)
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[DocumentMetadata]:
        """
        List documents with pagination.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List[DocumentMetadata]: List of document metadata
        """
        return self.doc_repository.list_documents(limit, offset)
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its associated data.
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            DocumentProcessingError: If deletion fails
        """
        try:
            # Delete from vector storage first
            self.vector_storage.delete_document_embeddings(document_id)
            
            # Delete from database (cascades to chunks)
            success = self.doc_repository.delete_document(document_id)
            
            return success
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to delete document: {str(e)}")
    
    def search_similar_chunks(self, query: str, top_k: int = 5, 
                            document_ids: Optional[List[str]] = None) -> List[DocumentChunk]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            document_ids: Optional list of document IDs to filter by
            
        Returns:
            List[DocumentChunk]: Similar chunks with similarity scores
            
        Raises:
            DocumentProcessingError: If search fails
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_query_embedding(query)
            
            # Perform vector similarity search
            similar_chunks = self.vector_storage.similarity_search(query_embedding, top_k * 2)  # Get more for filtering
            
            # Filter by document IDs if specified
            if document_ids:
                similar_chunks = [
                    chunk for chunk in similar_chunks 
                    if chunk.document_id in document_ids
                ]
            
            # Return top_k results
            return similar_chunks[:top_k]
            
        except (EmbeddingError, VectorStorageError) as e:
            raise DocumentProcessingError(f"Similarity search failed: {str(e)}")
        except Exception as e:
            raise DocumentProcessingError(f"Search failed: {str(e)}")
    
    def update_document_embeddings(self, document_id: str) -> bool:
        """
        Regenerate and update embeddings for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if update was successful
            
        Raises:
            DocumentProcessingError: If update fails
        """
        try:
            # Get document chunks
            chunks = self.get_document_chunks(document_id)
            
            if not chunks:
                return False
            
            # Delete existing embeddings from vector storage
            self.vector_storage.delete_document_embeddings(document_id)
            
            # Generate new embeddings
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings(texts)
            
            # Update chunks with new embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
                # Update in database
                self.chunk_repository.update_chunk_embedding(chunk.id, embedding)
            
            # Store new embeddings in vector storage
            self.vector_storage.store_embeddings(chunks)
            
            return True
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to update embeddings: {str(e)}")
    
    def get_storage_statistics(self) -> dict:
        """
        Get storage statistics.
        
        Returns:
            dict: Storage statistics
        """
        try:
            # Get document count from database
            documents = self.list_documents(limit=1000)  # Get a reasonable sample
            total_documents = len(documents)
            
            # Count documents by status
            status_counts = {}
            for doc in documents:
                status = doc.processing_status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Get vector storage stats
            vector_stats = self.vector_storage.get_storage_stats()
            
            # Get embedding service info
            embedding_info = self.embedding_service.get_model_info()
            
            return {
                "documents": {
                    "total": total_documents,
                    "by_status": status_counts
                },
                "vector_storage": vector_stats,
                "embedding_service": embedding_info
            }
            
        except Exception as e:
            return {"error": f"Failed to get statistics: {str(e)}"}
    
    def health_check(self) -> dict:
        """
        Perform health check on all storage components.
        
        Returns:
            dict: Health check results
        """
        health = {
            "database": False,
            "vector_storage": False,
            "embedding_service": False,
            "overall": False
        }
        
        try:
            # Test database connection
            test_docs = self.doc_repository.list_documents(limit=1)
            health["database"] = True
        except Exception as e:
            health["database_error"] = str(e)
            health["database"] = False
        
        try:
            # Test vector storage
            stats = self.vector_storage.get_storage_stats()
            health["vector_storage"] = True
        except Exception as e:
            health["vector_storage_error"] = str(e)
            health["vector_storage"] = False
        
        try:
            # Test embedding service
            test_embedding = self.embedding_service.generate_query_embedding("test")
            health["embedding_service"] = len(test_embedding) > 0
        except Exception as e:
            health["embedding_service_error"] = str(e)
            health["embedding_service"] = False
        
        # Overall health
        health["overall"] = all([
            health["database"],
            health["vector_storage"],
            health["embedding_service"]
        ])
        
        return health
    
    def clear_all_data(self):
        """
        Clear all stored data (for testing/development).
        
        Raises:
            DocumentProcessingError: If clearing fails
        """
        try:
            # Clear vector storage
            self.vector_storage.clear_all_data()
            
            # Clear database would require more careful implementation
            # For now, we'll just clear the vector storage
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to clear data: {str(e)}")