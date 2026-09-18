"""
Legacy mock search functions - kept for backward compatibility.
These are deprecated in favor of the new tool interfaces.
"""
import logging
from typing import List, Dict, Any
from app.tools.mock_database import MockSearchDatabase

logger = logging.getLogger(__name__)

# Initialize the mock database
mock_db = MockSearchDatabase()


def mock_search_tool(search_query: str, search_type: str = "general") -> List[Dict[str, Any]]:
    """
    Legacy mock search tool - use mock_database instead.
    """
    logger.warning("mock_search_tool is deprecated, use MockSearchDatabase instead")
    result = mock_db.semantic_search(search_query)
    return [doc.model_dump() for doc in result.documents]


def mock_incident_search(incident_id: str) -> Dict[str, Any]:
    """
    Legacy incident search - use mock_database instead.
    """
    logger.warning("mock_incident_search is deprecated, use MockSearchDatabase instead")
    doc = mock_db.get_document(incident_id)
    return doc.model_dump() if doc else None


def mock_service_search(service_name: str) -> List[Dict[str, Any]]:
    """
    Legacy service search - use mock_database instead.
    """
    logger.warning("mock_service_search is deprecated, use MockSearchDatabase instead")
    result = mock_db.search_by_service(service_name)
    return [doc.model_dump() for doc in result.documents]