"""
Configuration settings for the investigation system.
"""
import os
from typing import Optional


class Settings:
    """Application settings."""
    
    # Maximum number of investigation iterations
    MAX_ITERATIONS: int = 5
    
    # Minimum evidence items required for sufficiency
    MIN_EVIDENCE_ITEMS: int = 2
    
    # Logging level
    LOG_LEVEL: str = "INFO"
    
    # Mock data settings
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
    
    # Search settings
    MAX_SEARCH_RESULTS: int = 10
    SEARCH_TIMEOUT: int = 30
    
    # PostgreSQL configuration
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DATABASE: str = os.getenv("POSTGRES_DATABASE", "investigation_ai")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_POOL_SIZE: int = int(os.getenv("POSTGRES_POOL_SIZE", "10"))
    
    # Qdrant configuration
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "document_chunks")
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY")
    QDRANT_TIMEOUT: int = int(os.getenv("QDRANT_TIMEOUT", "30"))
    
    # OpenAI configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_EMBEDDING_DIMENSION: int = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", "1536"))
    
    # Embedding settings (fallback to sentence-transformers if OpenAI not configured)
    USE_OPENAI_EMBEDDINGS: bool = bool(os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    # Chunking settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # Ingestion settings
    INGESTION_BATCH_SIZE: int = int(os.getenv("INGESTION_BATCH_SIZE", "100"))
    
    @property
    def postgres_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
    
    @property
    def qdrant_url(self) -> str:
        """Generate Qdrant connection URL."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"
    
    @property
    def effective_embedding_dimension(self) -> int:
        """Get the effective embedding dimension based on configuration."""
        return self.OPENAI_EMBEDDING_DIMENSION if self.USE_OPENAI_EMBEDDINGS else self.EMBEDDING_DIMENSION


settings = Settings()