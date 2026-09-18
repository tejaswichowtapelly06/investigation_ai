"""
Tool provider interface and registry for dependency injection.
This provides clean separation between agents and data sources.
"""
from typing import List, Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from app.tools.interfaces import SearchTool, SearchFilters, DocumentResult, SearchResult


class SearchToolProvider(Protocol):
    """Protocol for search tool providers."""
    
    def get_search_tool(self) -> SearchTool:
        """Return a SearchTool instance."""
        ...


class EvidenceToolProvider(Protocol):
    """Protocol for evidence analysis tool providers."""
    
    def extract_evidence(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """Extract evidence from documents."""
        ...
    
    def detect_contradictions(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """Detect contradictions in documents."""
        ...
    
    def compare_incidents(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """Compare incidents in documents."""
        ...


class ToolRegistry:
    """
    Registry for tool providers.
    Allows swapping implementations (mock → Qdrant/PostgreSQL) without changing agents.
    This is a dependency injection container that can be passed to agents.
    """
    
    def __init__(self):
        self._search_provider: Optional[SearchToolProvider] = None
        self._evidence_provider: Optional[EvidenceToolProvider] = None
    
    def register_search_provider(self, provider: SearchToolProvider) -> None:
        """Register a search tool provider."""
        self._search_provider = provider
    
    def register_evidence_provider(self, provider: EvidenceToolProvider) -> None:
        """Register an evidence tool provider."""
        self._evidence_provider = provider
    
    def get_search_tool(self) -> SearchTool:
        """Get the registered search tool."""
        if self._search_provider is None:
            raise ValueError("No search provider registered")
        return self._search_provider.get_search_tool()
    
    def get_evidence_tool(self) -> EvidenceToolProvider:
        """Get the registered evidence tool provider."""
        if self._evidence_provider is None:
            raise ValueError("No evidence provider registered")
        return self._evidence_provider
    
    def has_search_provider(self) -> bool:
        """Check if a search provider is registered."""
        return self._search_provider is not None
    
    def has_evidence_provider(self) -> bool:
        """Check if an evidence provider is registered."""
        return self._evidence_provider is not None


def create_default_registry() -> ToolRegistry:
    """
    Create a tool registry with default mock providers for development/testing.
    This function should be used to create the registry, which is then passed to the workflow.
    """
    from app.tools.mock_database import MockSearchDatabase
    from app.tools.mock_analysis import MockEvidenceAnalysis
    
    class MockSearchProvider:
        def get_search_tool(self) -> SearchTool:
            return MockSearchDatabase()
    
    class MockEvidenceProvider:
        def extract_evidence(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
            from app.tools.analysis_functions import extract_evidence_claims
            claims = extract_evidence_claims(documents)
            return [claim.model_dump() for claim in claims]
        
        def detect_contradictions(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
            from app.tools.analysis_functions import detect_contradictions
            contradictions = detect_contradictions(documents)
            return [contr.model_dump() for contr in contradictions]
        
        def compare_incidents(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
            from app.tools.analysis_functions import compare_all_incidents
            comparisons = compare_all_incidents(documents)
            return [comp.model_dump() for comp in comparisons]
    
    registry = ToolRegistry()
    registry.register_search_provider(MockSearchProvider())
    registry.register_evidence_provider(MockEvidenceProvider())
    
    return registry


def create_production_registry() -> ToolRegistry:
    """
    Create a tool registry with production providers (Qdrant + PostgreSQL).
    This function should be used when USE_MOCK_DATA is set to false.
    Falls back to mock providers if production services are unavailable.
    """
    from app.config.settings import settings
    from app.tools.production_search import ProductionSearchTool
    from app.tools.production_evidence import ProductionEvidenceTool
    
    class ProductionSearchProvider:
        def __init__(self):
            self._search_tool = ProductionSearchTool()
            self._search_tool.initialize()
        
        def get_search_tool(self) -> SearchTool:
            return self._search_tool
    
    class ProductionEvidenceProvider:
        def __init__(self):
            self._evidence_tool = ProductionEvidenceTool()
            self._evidence_tool.initialize()
        
        def extract_evidence(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
            return self._evidence_tool.extract_evidence(documents)
        
        def detect_contradictions(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
            return self._evidence_tool.detect_contradictions(documents)
        
        def compare_incidents(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
            return self._evidence_tool.compare_incidents(documents)
    
    registry = ToolRegistry()
    
    try:
        registry.register_search_provider(ProductionSearchProvider())
        registry.register_evidence_provider(ProductionEvidenceProvider())
        logger.info("Production tool registry created successfully")
    except Exception as e:
        logger.error(f"Failed to create production registry, falling back to mock: {e}")
        return create_default_registry()
    
    return registry


# Global registry instance for backward compatibility during transition
# TODO: Remove this after all callers are updated to use dependency injection
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry (deprecated).
    
    This is a temporary backward-compatibility function during the transition
    to proper dependency injection. New code should pass ToolRegistry instances
    directly to agents instead of using this global singleton.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = create_default_registry()
    return _global_registry


def register_default_providers() -> None:
    """
    Register default providers in the global registry (deprecated).
    
    This function is deprecated. Use create_default_registry() instead.
    """
    global _global_registry
    _global_registry = create_default_registry()