"""
Production search tool implementation using Qdrant and PostgreSQL.
Implements the SearchTool interface with hybrid retrieval (semantic + metadata).
"""
import logging
from typing import List, Dict, Any, Optional
from app.tools.interfaces import SearchTool, DocumentResult, SearchFilters, SearchResult
from app.repositories.qdrant_repository import QdrantRepository
from app.repositories.postgres_repository import PostgresRepository
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ProductionSearchTool(SearchTool):
    """Production search tool using Qdrant for semantic search and PostgreSQL for metadata search."""
    
    def __init__(self):
        self._qdrant_repo = QdrantRepository()
        self._postgres_repo = PostgresRepository()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize repositories."""
        if self._initialized:
            return True
        
        try:
            self._qdrant_repo.initialize()
            self._postgres_repo.initialize()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize production search tool: {e}")
            return False
    
    def semantic_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Perform semantic search using Qdrant.
        Hybrid approach: semantic relevance + metadata from PostgreSQL.
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Get semantic results from Qdrant
            qdrant_results = self._qdrant_repo.semantic_search(query, limit)
            
            # Convert to SearchResult with full metadata from PostgreSQL
            results = []
            for hit in qdrant_results:
                payload = hit['payload']
                document_id = payload.get('document_id')
                
                # Get full document metadata from PostgreSQL
                doc = self._postgres_repo.get_document_by_id(document_id)
                if doc:
                    result = SearchResult(
                        document_id=doc.document_id,
                        document_type=doc.document_type,
                        title=doc.title,
                        service=doc.service,
                        date=doc.date,
                        version=doc.version,
                        content=payload.get('content', doc.content),
                        relevance_score=hit['score'],
                        metadata=doc.metadata
                    )
                    results.append(result)
            
            logger.info(f"Semantic search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def metadata_search(self, filters: SearchFilters, limit: int = 10) -> List[SearchResult]:
        """Search by metadata fields using PostgreSQL."""
        if not self._initialized:
            self.initialize()
        
        try:
            docs = self._postgres_repo.search_by_metadata(filters)
            
            results = [
                SearchResult(
                    document_id=doc.document_id,
                    document_type=doc.document_type,
                    title=doc.title,
                    service=doc.service,
                    date=doc.date,
                    version=doc.version,
                    content=doc.content,
                    relevance_score=0.0,
                    metadata=doc.metadata
                )
                for doc in docs
            ]
            
            logger.info(f"Metadata search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in metadata search: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[DocumentResult]:
        """Retrieve a specific document by ID."""
        if not self._initialized:
            self.initialize()
        
        return self._postgres_repo.get_document_by_id(document_id)
    
    def search_related_documents(self, document_id: str, limit: int = 10) -> List[SearchResult]:
        """Find documents related to a given document."""
        if not self._initialized:
            self.initialize()
        
        try:
            related = self._qdrant_repo.search_related_documents(document_id, limit)
            
            results = []
            for hit in related:
                payload = hit['payload']
                doc_id = payload.get('document_id')
                doc = self._postgres_repo.get_document_by_id(doc_id)
                if doc:
                    result = SearchResult(
                        document_id=doc.document_id,
                        document_type=doc.document_type,
                        title=doc.title,
                        service=doc.service,
                        date=doc.date,
                        version=doc.version,
                        content=payload.get('content', doc.content),
                        relevance_score=hit['score'],
                        metadata=doc.metadata
                    )
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error searching related documents: {e}")
            return []
    
    def search_historical_incidents(self, service: str, symptom: str, limit: int = 10) -> List[SearchResult]:
        """Search for historical incidents with similar symptoms."""
        if not self._initialized:
            self.initialize()
        
        try:
            filters = SearchFilters(service=service, document_type="incident_report")
            query = f"{symptom} incident {service}"
            return self.semantic_search_with_filters(query, filters, limit)
        except Exception as e:
            logger.error(f"Error searching historical incidents: {e}")
            return []
    
    def search_by_service(self, service: str, limit: int = 10) -> List[SearchResult]:
        """Search for documents related to a specific service."""
        filters = SearchFilters(service=service)
        return self.metadata_search(filters, limit)
    
    def search_by_version(self, version: str, limit: int = 10) -> List[SearchResult]:
        """Search for documents related to a specific version."""
        filters = SearchFilters(version=version)
        return self.metadata_search(filters, limit)
    
    def search_by_date_range(self, service: str, start_date: str, end_date: str, limit: int = 10) -> List[SearchResult]:
        """Search documents within a date range."""
        filters = SearchFilters(service=service, date_range=(start_date, end_date))
        return self.metadata_search(filters, limit)
    
    def semantic_search_with_filters(self, query: str, filters: SearchFilters, limit: int = 10) -> List[SearchResult]:
        """
        Hybrid retrieval: semantic search with metadata filters.
        Combines Qdrant semantic search with PostgreSQL metadata constraints.
        """
        if not self._initialized:
            self.initialize()
        
        try:
            qdrant_results = self._qdrant_repo.semantic_search_with_filters(query, filters, limit)
            
            results = []
            for hit in qdrant_results:
                payload = hit['payload']
                document_id = payload.get('document_id')
                
                doc = self._postgres_repo.get_document_by_id(document_id)
                if doc:
                    result = SearchResult(
                        document_id=doc.document_id,
                        document_type=doc.document_type,
                        title=doc.title,
                        service=doc.service,
                        date=doc.date,
                        version=doc.version,
                        content=payload.get('content', doc.content),
                        relevance_score=hit['score'],
                        metadata=doc.metadata
                    )
                    results.append(result)
            
            logger.info(f"Hybrid search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return self.metadata_search(filters, limit)
