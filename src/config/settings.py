"""
Configuration settings for the Knowledge-base Search Engine.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str = "sqlite:///knowledge_base.db"
    echo: bool = False


@dataclass
class EmbeddingConfig:
    """Embedding service configuration."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 32
    openai_api_key: Optional[str] = None


@dataclass
class VectorStorageConfig:
    """Vector storage configuration."""
    storage_type: str = "faiss"  # faiss, pinecone, chroma
    index_path: str = "data/vector_index"
    similarity_metric: str = "cosine"


@dataclass
class LLMConfig:
    """LLM service configuration."""
    provider: str = "gemini"  # gemini, openai, huggingface, local
    model_name: str = "gemini-1.5-flash"
    api_key: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.1


@dataclass
class DocumentProcessingConfig:
    """Document processing configuration."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    supported_formats: list = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ["pdf", "txt"]


@dataclass
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000"]


@dataclass
class AppConfig:
    """Main application configuration."""
    database: DatabaseConfig
    embedding: EmbeddingConfig
    vector_storage: VectorStorageConfig
    llm: LLMConfig
    document_processing: DocumentProcessingConfig
    api: APIConfig
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        return cls(
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///knowledge_base.db"),
                echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
            ),
            embedding=EmbeddingConfig(
                model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
                dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
                batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
                openai_api_key=os.getenv("OPENAI_API_KEY")
            ),
            vector_storage=VectorStorageConfig(
                storage_type=os.getenv("VECTOR_STORAGE_TYPE", "faiss"),
                index_path=os.getenv("VECTOR_INDEX_PATH", "data/vector_index"),
                similarity_metric=os.getenv("SIMILARITY_METRIC", "cosine")
            ),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "gemini"),
                model_name=os.getenv("LLM_MODEL", "gemini-1.5-flash"),
                api_key=os.getenv("GOOGLE_AI_API_KEY"),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.1"))
            ),
            document_processing=DocumentProcessingConfig(
                chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
                max_file_size=int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
            ),
            api=APIConfig(
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                debug=os.getenv("API_DEBUG", "false").lower() == "true"
            )
        )


# Global configuration instance
config = AppConfig.from_env()