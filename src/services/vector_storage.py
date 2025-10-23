"""
Vector storage service using FAISS for development and scalable options for production.
"""
import os
import pickle
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import faiss
from src.services.interfaces import VectorStorageInterface
from src.models.document import DocumentChunk
from src.utils.exceptions import VectorStorageError
from src.config.settings import config


class FAISSVectorStorage(VectorStorageInterface):
    """FAISS-based vector storage for development and local deployment."""
    
    def __init__(self, index_path: str = None, dimension: int = None):
        """
        Initialize FAISS vector storage.
        
        Args:
            index_path: Path to store the FAISS index
            dimension: Dimension of the embedding vectors
        """
        self.index_path = Path(index_path or config.vector_storage.index_path)
        self.dimension = dimension or config.embedding.dimension
        
        # Create directory if it doesn't exist
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # FAISS index and metadata storage
        self.index = None
        self.chunk_metadata = {}  # Maps vector ID to DocumentChunk
        self.id_to_vector_id = {}  # Maps chunk ID to vector ID
        self.next_vector_id = 0
        
        # Initialize or load existing index
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize or load existing FAISS index."""
        try:
            if self._index_exists():
                self._load_index()
            else:
                self._create_new_index()
        except Exception as e:
            raise VectorStorageError(f"Failed to initialize FAISS index: {str(e)}")
    
    def _index_exists(self) -> bool:
        """Check if index files exist."""
        index_file = self.index_path / "faiss.index"
        metadata_file = self.index_path / "metadata.pkl"
        return index_file.exists() and metadata_file.exists()
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        try:
            # Create L2 (Euclidean) index for similarity search
            # For cosine similarity, we'll normalize vectors before adding
            self.index = faiss.IndexFlatL2(self.dimension)
            self.chunk_metadata = {}
            self.id_to_vector_id = {}
            self.next_vector_id = 0
            
            # Save the empty index
            self._save_index()
            
        except Exception as e:
            raise VectorStorageError(f"Failed to create FAISS index: {str(e)}")
    
    def _load_index(self):
        """Load existing FAISS index and metadata."""
        try:
            index_file = self.index_path / "faiss.index"
            metadata_file = self.index_path / "metadata.pkl"
            
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            
            # Load metadata
            with open(metadata_file, 'rb') as f:
                data = pickle.load(f)
                self.chunk_metadata = data.get('chunk_metadata', {})
                self.id_to_vector_id = data.get('id_to_vector_id', {})
                self.next_vector_id = data.get('next_vector_id', 0)
                
        except Exception as e:
            raise VectorStorageError(f"Failed to load FAISS index: {str(e)}")
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            index_file = self.index_path / "faiss.index"
            metadata_file = self.index_path / "metadata.pkl"
            
            # Save FAISS index
            faiss.write_index(self.index, str(index_file))
            
            # Save metadata
            metadata = {
                'chunk_metadata': self.chunk_metadata,
                'id_to_vector_id': self.id_to_vector_id,
                'next_vector_id': self.next_vector_id
            }
            
            with open(metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
                
        except Exception as e:
            raise VectorStorageError(f"Failed to save FAISS index: {str(e)}")
    
    def store_embeddings(self, chunks: List[DocumentChunk]) -> None:
        """
        Store document chunk embeddings in the vector database.
        
        Args:
            chunks: List of document chunks with embeddings
            
        Raises:
            VectorStorageError: If storage fails
        """
        if not chunks:
            return
        
        try:
            vectors = []
            vector_ids = []
            
            for chunk in chunks:
                if not chunk.embedding:
                    raise VectorStorageError(f"Chunk {chunk.id} has no embedding")
                
                if len(chunk.embedding) != self.dimension:
                    raise VectorStorageError(
                        f"Embedding dimension mismatch: expected {self.dimension}, "
                        f"got {len(chunk.embedding)}"
                    )
                
                # Normalize vector for cosine similarity
                vector = np.array(chunk.embedding, dtype=np.float32)
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
                
                vectors.append(vector)
                
                # Assign vector ID
                vector_id = self.next_vector_id
                vector_ids.append(vector_id)
                
                # Store metadata
                self.chunk_metadata[vector_id] = chunk
                self.id_to_vector_id[chunk.id] = vector_id
                
                self.next_vector_id += 1
            
            # Add vectors to FAISS index
            vectors_array = np.array(vectors)
            self.index.add(vectors_array)
            
            # Save updated index
            self._save_index()
            
        except VectorStorageError:
            raise
        except Exception as e:
            raise VectorStorageError(f"Failed to store embeddings: {str(e)}")
    
    def similarity_search(self, query_embedding: List[float], top_k: int = 5) -> List[DocumentChunk]:
        """
        Perform similarity search and return top-k chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            
        Returns:
            List[DocumentChunk]: Top-k most similar chunks
            
        Raises:
            VectorStorageError: If search fails
        """
        if not query_embedding:
            raise VectorStorageError("Query embedding cannot be empty")
        
        if len(query_embedding) != self.dimension:
            raise VectorStorageError(
                f"Query embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(query_embedding)}"
            )
        
        if self.index.ntotal == 0:
            return []  # No vectors stored yet
        
        try:
            # Normalize query vector for cosine similarity
            query_vector = np.array(query_embedding, dtype=np.float32)
            norm = np.linalg.norm(query_vector)
            if norm > 0:
                query_vector = query_vector / norm
            
            # Reshape for FAISS (expects 2D array)
            query_vector = query_vector.reshape(1, -1)
            
            # Perform search
            k = min(top_k, self.index.ntotal)
            distances, indices = self.index.search(query_vector, k)
            
            # Convert results to DocumentChunks
            results = []
            for i, vector_id in enumerate(indices[0]):
                if vector_id in self.chunk_metadata:
                    chunk = self.chunk_metadata[vector_id]
                    # Add similarity score (convert L2 distance to similarity)
                    similarity_score = 1.0 / (1.0 + distances[0][i])
                    
                    # Create a copy of the chunk with similarity score
                    result_chunk = DocumentChunk(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        chunk_index=chunk.chunk_index,
                        start_position=chunk.start_position,
                        end_position=chunk.end_position,
                        embedding=chunk.embedding
                    )
                    # Store similarity score as an attribute (not in the dataclass)
                    setattr(result_chunk, 'similarity_score', similarity_score)
                    
                    results.append(result_chunk)
            
            return results
            
        except VectorStorageError:
            raise
        except Exception as e:
            raise VectorStorageError(f"Similarity search failed: {str(e)}")
    
    def delete_document_embeddings(self, document_id: str) -> None:
        """
        Delete all embeddings for a document.
        
        Args:
            document_id: ID of the document to delete
            
        Raises:
            VectorStorageError: If deletion fails
        """
        try:
            # Find all vector IDs for this document
            vector_ids_to_remove = []
            chunk_ids_to_remove = []
            
            for vector_id, chunk in self.chunk_metadata.items():
                if chunk.document_id == document_id:
                    vector_ids_to_remove.append(vector_id)
                    chunk_ids_to_remove.append(chunk.id)
            
            if not vector_ids_to_remove:
                return  # No vectors to remove
            
            # Remove from metadata
            for vector_id in vector_ids_to_remove:
                del self.chunk_metadata[vector_id]
            
            for chunk_id in chunk_ids_to_remove:
                if chunk_id in self.id_to_vector_id:
                    del self.id_to_vector_id[chunk_id]
            
            # FAISS doesn't support direct deletion, so we need to rebuild the index
            self._rebuild_index_without_vectors(vector_ids_to_remove)
            
            # Save updated index
            self._save_index()
            
        except Exception as e:
            raise VectorStorageError(f"Failed to delete document embeddings: {str(e)}")
    
    def _rebuild_index_without_vectors(self, vector_ids_to_remove: List[int]):
        """Rebuild FAISS index excluding specified vector IDs."""
        try:
            # Get all vectors except the ones to remove
            remaining_vectors = []
            new_metadata = {}
            new_id_mapping = {}
            new_vector_id = 0
            
            for vector_id, chunk in self.chunk_metadata.items():
                if vector_id not in vector_ids_to_remove:
                    # Get the vector from the index
                    vector = self.index.reconstruct(vector_id)
                    remaining_vectors.append(vector)
                    
                    # Update metadata with new vector ID
                    new_metadata[new_vector_id] = chunk
                    new_id_mapping[chunk.id] = new_vector_id
                    new_vector_id += 1
            
            # Create new index
            new_index = faiss.IndexFlatL2(self.dimension)
            
            if remaining_vectors:
                vectors_array = np.array(remaining_vectors)
                new_index.add(vectors_array)
            
            # Update instance variables
            self.index = new_index
            self.chunk_metadata = new_metadata
            self.id_to_vector_id = new_id_mapping
            self.next_vector_id = new_vector_id
            
        except Exception as e:
            raise VectorStorageError(f"Failed to rebuild index: {str(e)}")
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[DocumentChunk]:
        """
        Get a chunk by its ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            DocumentChunk or None: The chunk if found
        """
        vector_id = self.id_to_vector_id.get(chunk_id)
        if vector_id is not None:
            return self.chunk_metadata.get(vector_id)
        return None
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dict: Storage statistics
        """
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "index_path": str(self.index_path),
            "total_chunks": len(self.chunk_metadata),
            "next_vector_id": self.next_vector_id
        }
    
    def clear_all_data(self):
        """Clear all stored data and create a new empty index."""
        try:
            self._create_new_index()
        except Exception as e:
            raise VectorStorageError(f"Failed to clear data: {str(e)}")


class VectorStorageFactory:
    """Factory for creating vector storage instances."""
    
    @staticmethod
    def create_storage(storage_type: str = None, **kwargs) -> VectorStorageInterface:
        """
        Create a vector storage instance.
        
        Args:
            storage_type: Type of storage ('faiss', 'pinecone', 'chroma')
            **kwargs: Additional arguments for the storage
            
        Returns:
            VectorStorageInterface: Storage instance
            
        Raises:
            VectorStorageError: If storage type is not supported
        """
        storage_type = storage_type or config.vector_storage.storage_type
        
        if storage_type.lower() == "faiss":
            return FAISSVectorStorage(**kwargs)
        else:
            raise VectorStorageError(f"Unsupported storage type: {storage_type}")