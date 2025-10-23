"""
Embedding generation service using sentence transformers or OpenAI.
"""
import os
import pickle
from typing import List, Optional, Dict, Any
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from src.services.interfaces import EmbeddingServiceInterface
from src.utils.exceptions import EmbeddingError
from src.config.settings import config


class EmbeddingService(EmbeddingServiceInterface):
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = None, cache_dir: str = "data/embeddings_cache"):
        """
        Initialize embedding service.
        
        Args:
            model_name: Name of the embedding model to use
            cache_dir: Directory for caching embeddings
        """
        self.model_name = model_name or config.embedding.model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.embedding_dimension = config.embedding.dimension
        self.batch_size = config.embedding.batch_size
        self.provider = None
        
        # Initialize model
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model."""
        try:
            if config.embedding.openai_api_key and "openai" in self.model_name.lower():
                # Use OpenAI embeddings
                self._init_openai_embeddings()
            else:
                # Use sentence transformers
                self._init_sentence_transformer()
                
        except Exception as e:
            raise EmbeddingError(f"Failed to load embedding model: {str(e)}")
    
    def _init_sentence_transformer(self):
        """Initialize sentence transformer model."""
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            self.provider = "sentence_transformers"
        except Exception as e:
            raise EmbeddingError(f"Failed to load sentence transformer model: {str(e)}")
    
    def _init_openai_embeddings(self):
        """Initialize OpenAI embeddings."""
        try:
            import openai
            openai.api_key = config.embedding.openai_api_key
            self.provider = "openai"
            self.embedding_dimension = 1536  # OpenAI text-embedding-ada-002 dimension
        except ImportError:
            raise EmbeddingError("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize OpenAI embeddings: {str(e)}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []
        
        try:
            # Check cache first
            cached_embeddings = self._get_cached_embeddings(texts)
            if cached_embeddings:
                return cached_embeddings
            
            # Generate new embeddings
            if self.provider == "sentence_transformers":
                embeddings = self._generate_with_sentence_transformer(texts)
            elif self.provider == "openai":
                embeddings = self._generate_with_openai(texts)
            else:
                raise EmbeddingError(f"Unknown embedding provider: {self.provider}")
            
            # Cache the embeddings
            self._cache_embeddings(texts, embeddings)
            
            return embeddings
            
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {str(e)}")
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a single query.
        
        Args:
            query: Query text
            
        Returns:
            List[float]: Embedding vector
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not query or not query.strip():
            raise EmbeddingError("Query cannot be empty")
        
        embeddings = self.generate_embeddings([query.strip()])
        return embeddings[0] if embeddings else []
    
    def _generate_with_sentence_transformer(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence transformer."""
        try:
            # Process in batches to manage memory
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i + self.batch_size]
                batch_embeddings = self.model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
                
                # Convert to list of lists
                for embedding in batch_embeddings:
                    all_embeddings.append(embedding.tolist())
            
            return all_embeddings
            
        except Exception as e:
            raise EmbeddingError(f"Sentence transformer embedding failed: {str(e)}")
    
    def _generate_with_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            import openai
            
            all_embeddings = []
            
            # Process in batches (OpenAI has rate limits)
            batch_size = min(self.batch_size, 100)  # OpenAI limit
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                response = openai.Embedding.create(
                    model="text-embedding-ada-002",
                    input=batch_texts
                )
                
                for item in response['data']:
                    all_embeddings.append(item['embedding'])
            
            return all_embeddings
            
        except Exception as e:
            raise EmbeddingError(f"OpenAI embedding failed: {str(e)}")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        import hashlib
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()
    
    def _get_cached_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Get cached embeddings if available.
        
        Args:
            texts: List of texts
            
        Returns:
            List of embeddings if all are cached, None otherwise
        """
        try:
            cached_embeddings = []
            
            for text in texts:
                cache_key = self._get_cache_key(text)
                cache_file = self.cache_dir / f"{cache_key}.pkl"
                
                if cache_file.exists():
                    with open(cache_file, 'rb') as f:
                        embedding = pickle.load(f)
                        cached_embeddings.append(embedding)
                else:
                    # If any text is not cached, return None
                    return None
            
            return cached_embeddings
            
        except Exception:
            # If cache reading fails, generate fresh embeddings
            return None
    
    def _cache_embeddings(self, texts: List[str], embeddings: List[List[float]]):
        """
        Cache embeddings for future use.
        
        Args:
            texts: List of texts
            embeddings: Corresponding embeddings
        """
        try:
            for text, embedding in zip(texts, embeddings):
                cache_key = self._get_cache_key(text)
                cache_file = self.cache_dir / f"{cache_key}.pkl"
                
                with open(cache_file, 'wb') as f:
                    pickle.dump(embedding, f)
                    
        except Exception:
            # Cache failures are not critical
            pass
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.
        
        Returns:
            int: Embedding dimension
        """
        return self.embedding_dimension
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate an embedding vector.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            EmbeddingError: If embedding is invalid
        """
        if not embedding:
            raise EmbeddingError("Embedding cannot be empty")
        
        if len(embedding) != self.embedding_dimension:
            raise EmbeddingError(
                f"Embedding dimension mismatch: expected {self.embedding_dimension}, "
                f"got {len(embedding)}"
            )
        
        if not all(isinstance(x, (int, float)) for x in embedding):
            raise EmbeddingError("Embedding must contain only numeric values")
        
        # Check for NaN or infinite values
        if any(np.isnan(x) or np.isinf(x) for x in embedding):
            raise EmbeddingError("Embedding contains NaN or infinite values")
        
        return True
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score (-1 to 1)
            
        Raises:
            EmbeddingError: If embeddings are invalid
        """
        self.validate_embedding(embedding1)
        self.validate_embedding(embedding2)
        
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Compute cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            raise EmbeddingError(f"Failed to compute similarity: {str(e)}")
    
    def clear_cache(self):
        """Clear the embedding cache."""
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
        except Exception:
            pass  # Cache clearing failures are not critical
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dict: Model information
        """
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "embedding_dimension": self.embedding_dimension,
            "batch_size": self.batch_size,
            "cache_dir": str(self.cache_dir)
        }