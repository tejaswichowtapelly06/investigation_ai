"""
Tool interfaces for document retrieval.
These interfaces define the contract for search tools that can be swapped
with real database implementations (Qdrant, PostgreSQL) later.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentResult(BaseModel):
    """Consistent structure for document search results."""
    document_id: str = Field(description="Unique document identifier")
    document_type: str = Field(description="Type of document (incident_report, postmortem, etc.)")
    title: str = Field(description="Document title")
    service: str = Field(default="", description="Service/component name")
    date: str = Field(default="", description="Document date")
    version: str = Field(default="", description="Version information")
    content: str = Field(default="", description="Document content or snippet")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Optional fields for specific document types
    incident_id: str = Field(default="", description="Incident ID if applicable")
    severity: str = Field(default="", description="Severity level if applicable")
    author: str = Field(default="", description="Document author")


class SearchFilters(BaseModel):
    """Filters for metadata search."""
    service: Optional[str] = None
    date_range: Optional[tuple[str, str]] = None  # (start_date, end_date)
    version: Optional[str] = None
    document_type: Optional[str] = None
    incident_id: Optional[str] = None


class SearchResult(BaseModel):
    """Result from a search operation."""
    documents: List[DocumentResult] = Field(default_factory=list)
    total_found: int = Field(default=0)
    search_metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchTool:
    """Base interface for search tools."""
    
    def semantic_search(self, query: str, filters: Optional[SearchFilters] = None) -> SearchResult:
        """
        Perform semantic search on document content.
        
        Args:
            query: Search query text
            filters: Optional filters to apply
            
        Returns:
            SearchResult with matching documents
        """
        raise NotImplementedError("semantic_search not implemented")
    
    def metadata_search(self, filters: SearchFilters) -> SearchResult:
        """
        Search by metadata fields (service, date, version, document_type).
        
        Args:
            filters: Search filters
            
        Returns:
            SearchResult with matching documents
        """
        raise NotImplementedError("metadata_search not implemented")
    
    def get_document(self, document_id: str) -> Optional[DocumentResult]:
        """
        Retrieve a specific document by ID.
        
        Args:
            document_id: Unique document identifier
            
        Returns:
            DocumentResult or None if not found
        """
        raise NotImplementedError("get_document not implemented")
    
    def search_related_documents(self, document_id: str) -> SearchResult:
        """
        Find documents related to a given document.
        
        Args:
            document_id: Source document ID
            
        Returns:
            SearchResult with related documents
        """
        raise NotImplementedError("search_related_documents not implemented")
    
    def search_historical_incidents(self, service: str, symptom: str) -> SearchResult:
        """
        Search for historical incidents with similar symptoms.
        
        Args:
            service: Service name
            symptom: Symptom description
            
        Returns:
            SearchResult with matching historical incidents
        """
        raise NotImplementedError("search_historical_incidents not implemented")
    
    def search_by_version(self, version: str) -> SearchResult:
        """
        Search for documents related to a specific version.
        
        Args:
            version: Version string
            
        Returns:
            SearchResult with matching documents
        """
        raise NotImplementedError("search_by_version not implemented")
    
    def search_by_service(self, service: str) -> SearchResult:
        """
        Search for documents related to a specific service.
        
        Args:
            service: Service name
            
        Returns:
            SearchResult with matching documents
        """
        raise NotImplementedError("search_by_service not implemented")