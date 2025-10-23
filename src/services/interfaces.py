"""
Interface definitions for service layer components.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, BinaryIO
from src.models.document import DocumentMetadata, DocumentChunk, ProcessedDocument, FileType
from src.models.query import QueryResult, SynthesizedAnswer, Citation


class DocumentIngestionInterface(ABC):
    """Interface for document ingestion service."""
    
    @abstractmethod
    def upload_document(self, file_content: BinaryIO, filename: str) -> DocumentMetadata:
        """Upload and process a document."""
        pass
    
    @abstractmethod
    def extract_text(self, file_path: str, file_type: FileType) -> str:
        """Extract text from a file."""
        pass
    
    @abstractmethod
    def chunk_document(self, text: str, document_id: str, chunk_size: int = 1000, overlap: int = 200) -> List[DocumentChunk]:
        """Split document into chunks."""
        pass
    
    @abstractmethod
    def store_document(self, document: ProcessedDocument) -> str:
        """Store processed document and return document ID."""
        pass


class EmbeddingServiceInterface(ABC):
    """Interface for embedding generation service."""
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass
    
    @abstractmethod
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a search query."""
        pass


class VectorStorageInterface(ABC):
    """Interface for vector storage operations."""
    
    @abstractmethod
    def store_embeddings(self, chunks: List[DocumentChunk]) -> None:
        """Store document chunk embeddings."""
        pass
    
    @abstractmethod
    def similarity_search(self, query_embedding: List[float], top_k: int = 5) -> List[DocumentChunk]:
        """Perform similarity search and return top-k chunks."""
        pass
    
    @abstractmethod
    def delete_document_embeddings(self, document_id: str) -> None:
        """Delete all embeddings for a document."""
        pass


class RAGEngineInterface(ABC):
    """Interface for RAG engine operations."""
    
    @abstractmethod
    def process_query(self, query: str) -> QueryResult:
        """Process a query and return results."""
        pass
    
    @abstractmethod
    def retrieve_relevant_chunks(self, query_embedding: List[float], top_k: int = 5) -> List[DocumentChunk]:
        """Retrieve relevant document chunks."""
        pass
    
    @abstractmethod
    def prepare_context(self, chunks: List[DocumentChunk]) -> str:
        """Prepare context for LLM from retrieved chunks."""
        pass


class AnswerSynthesizerInterface(ABC):
    """Interface for answer synthesis service."""
    
    @abstractmethod
    def synthesize_answer(self, query: str, context: str, sources: List[DocumentMetadata]) -> SynthesizedAnswer:
        """Generate synthesized answer from context."""
        pass
    
    @abstractmethod
    def construct_prompt(self, query: str, context: str) -> str:
        """Construct prompt for LLM."""
        pass
    
    @abstractmethod
    def extract_citations(self, answer: str, sources: List[DocumentMetadata]) -> List[Citation]:
        """Extract citations from generated answer."""
        pass


class QueryProcessorInterface(ABC):
    """Interface for query processing service."""
    
    @abstractmethod
    def process_query(self, query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> QueryResult:
        """Process a natural language query."""
        pass
    
    @abstractmethod
    def validate_query(self, query: str) -> bool:
        """Validate query format and content."""
        pass