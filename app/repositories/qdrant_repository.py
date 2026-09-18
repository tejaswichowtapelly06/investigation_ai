"""
Qdrant repository for semantic search and document embeddings.
"""
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny
from app.config.settings import settings
from app.tools.interfaces import DocumentResult, SearchFilters
from app.ingestion.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class QdrantRepository:
    """Repository for Qdrant vector database operations."""
    
    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._collection_name = settings.QDRANT_COLLECTION_NAME
        self._embedding_generator = EmbeddingGenerator()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Qdrant client and collection."""
        if self._initialized:
            return True
        
        try:
            # Initialize client
            self._client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.QDRANT_API_KEY,
                timeout=settings.QDRANT_TIMEOUT
            )
            
            # Check if collection exists, create if not
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self._collection_name not in collection_names:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(
                        size=settings.effective_embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self._collection_name}")
            
            # Initialize embedding generator
            self._embedding_generator.initialize()
            
            self._initialized = True
            logger.info("Qdrant repository initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant repository: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Qdrant is available."""
        if self._client is None:
            return False
        
        try:
            self._client.get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant availability check failed: {e}")
            return False
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search using query text.
        
        Returns list of dicts with: id, score, payload
        """
        if not self.is_available():
            logger.warning("Qdrant unavailable, returning empty list")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._embedding_generator.generate_embedding(query)
            if query_embedding is None:
                logger.error("Failed to generate query embedding")
                return []
            
            search_result = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=0.3  # Minimum similarity threshold
            )
            
            results = []
            for hit in search_result:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                })
            
            return results
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
    
    def semantic_search_with_filters(self, query: str, 
                                     filters: SearchFilters, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search with metadata filters."""
        if not self.is_available():
            logger.warning("Qdrant unavailable, returning empty list")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._embedding_generator.generate_embedding(query)
            if query_embedding is None:
                logger.error("Failed to generate query embedding")
                return []
            
            # Build Qdrant filter
            must_conditions = []
            
            if filters.service:
                must_conditions.append(FieldCondition(key="service", match=MatchValue(value=filters.service)))
            
            if filters.document_type:
                must_conditions.append(FieldCondition(key="document_type", match=MatchValue(value=filters.document_type)))
            
            if filters.version:
                must_conditions.append(FieldCondition(key="version", match=MatchValue(value=filters.version)))
            
            if filters.incident_id:
                # Search in payload metadata
                must_conditions.append(FieldCondition(key="metadata.incident_id", match=MatchValue(value=filters.incident_id)))
            
            qdrant_filter = Filter(must=must_conditions) if must_conditions else None
            
            search_result = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=limit,
                score_threshold=0.3
            )
            
            results = []
            for hit in search_result:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'payload': hit.payload
                })
            
            return results
        except Exception as e:
            logger.error(f"Error performing filtered semantic search: {e}")
            return []
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID from Qdrant."""
        if not self.is_available():
            return None
        
        try:
            result = self._client.retrieve(
                collection_name=self._collection_name,
                ids=[document_id]
            )
            
            if result:
                return {
                    'id': result[0].id,
                    'payload': result[0].payload
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    def search_related_documents(self, document_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find documents related to a given document."""
        if not self.is_available():
            return []
        
        try:
            # First get the document to retrieve its vector
            result = self._client.retrieve(
                collection_name=self._collection_name,
                ids=[document_id],
                with_vectors=True
            )
            
            if not result or not result[0].vector:
                return []
            
            # Use the document's vector to find similar documents
            search_result = self._client.search(
                collection_name=self._collection_name,
                query_vector=result[0].vector,
                limit=limit + 1,  # +1 to exclude the document itself
                score_threshold=0.4
            )
            
            # Filter out the document itself
            results = []
            for hit in search_result:
                if hit.id != document_id:
                    results.append({
                        'id': hit.id,
                        'score': hit.score,
                        'payload': hit.payload
                    })
            
            return results[:limit]
        except Exception as e:
            logger.error(f"Error searching related documents: {e}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from Qdrant."""
        if not self.is_available():
            return False
        
        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=[document_id]
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
