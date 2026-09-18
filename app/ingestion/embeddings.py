"""
Embedding generation using OpenAI or sentence-transformers.
"""
import logging
from typing import List, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""
    
    def __init__(self):
        self._openai_client = None
        self._sentence_model = None
        self._initialized = False
    
    def initialize(self):
        """Initialize the embedding model."""
        if self._initialized:
            return True
        
        if settings.USE_OPENAI_EMBEDDINGS and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info(f"Initialized OpenAI embeddings with model: {settings.OPENAI_EMBEDDING_MODEL}")
                self._initialized = True
                return True
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI embeddings: {e}")
                logger.info("Falling back to sentence-transformers")
        
        # Fallback to sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._sentence_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"Initialized sentence-transformers with model: {settings.EMBEDDING_MODEL}")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize sentence-transformers: {e}")
            return False
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        if not self._initialized:
            if not self.initialize():
                return None
        
        try:
            if self._openai_client:
                response = self._openai_client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text
                )
                return response.data[0].embedding
            elif self._sentence_model:
                return self._sentence_model.encode(text).tolist()
            else:
                logger.error("No embedding model initialized")
                return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts efficiently."""
        if not self._initialized:
            if not self.initialize():
                return [None] * len(texts)
        
        try:
            if self._openai_client:
                # OpenAI batch embedding
                response = self._openai_client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=texts
                )
                return [item.embedding for item in response.data]
            elif self._sentence_model:
                # Sentence-transformers batch encoding
                embeddings = self._sentence_model.encode(texts)
                return embeddings.tolist()
            else:
                logger.error("No embedding model initialized")
                return [None] * len(texts)
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return settings.effective_embedding_dimension
