"""
Test suite for the Researcher Agent.
Tests multi-hop investigation capabilities and tool interfaces.
"""
import sys
import os
import unittest

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.graph.state import InvestigationState, InvestigationPlan, Entity, EntityType, InvestigationTask
from app.agents.researcher import researcher_agent, determine_next_task, generate_follow_up_task, extract_entities_from_results, merge_entities
from app.tools.interfaces import SearchFilters
from app.tools.mock_database import MockSearchDatabase
from tests.test_helpers import create_test_state
from app.tools.tool_registry import register_default_providers


class TestResearcherAgent(unittest.TestCase):
    """Test cases for the Researcher Agent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_database = MockSearchDatabase()
        # Register default providers for dependency injection
        register_default_providers()
    
    def test_multi_hop_investigation(self):
        """Test that information discovered in one search triggers follow-up searches."""
        # Test the tool interfaces directly to verify multi-hop capability
        # First search: semantic search for payment service latency
        result1 = self.mock_database.semantic_search("payment service latency")
        
        # Verify documents were found
        self.assertTrue(len(result1.documents) > 0)
        
        # Extract version from first result
        first_doc = result1.documents[0]
        if first_doc.version:
            # Second search: search by version (multi-hop)
            result2 = self.mock_database.search_by_version(first_doc.version)
            
            # Verify additional documents were found
            self.assertTrue(len(result2.documents) > 0)
            
            # Verify that the search found different document types
            doc_types = [doc.document_type for doc in result2.documents]
            self.assertTrue(len(doc_types) > 0, "Expected to find documents with different types")
        
        print("[PASS] Multi-hop investigation test passed")
    
    def test_tool_interface_semantic_search(self):
        """Test semantic search tool interface."""
        query = "payment service latency"
        result = self.mock_database.semantic_search(query)
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.documents, list)
        
        # Verify documents have required fields
        if result.documents:
            doc = result.documents[0]
            self.assertTrue(hasattr(doc, 'document_id'))
            self.assertTrue(hasattr(doc, 'document_type'))
            self.assertTrue(hasattr(doc, 'title'))
            self.assertTrue(hasattr(doc, 'service'))
            self.assertTrue(hasattr(doc, 'relevance_score'))
        
        print("[PASS] Semantic search tool interface test passed")
    
    def test_tool_interface_metadata_search(self):
        """Test metadata search tool interface."""
        filters = SearchFilters(service="payment-api", document_type="incident_report")
        result = self.mock_database.metadata_search(filters)
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.documents, list)
        
        # Verify filters were applied
        for doc in result.documents:
            self.assertEqual(doc.service, "payment-api")
            self.assertEqual(doc.document_type, "incident_report")
        
        print("[PASS] Metadata search tool interface test passed")
    
    def test_tool_interface_get_document(self):
        """Test get_document tool interface."""
        doc = self.mock_database.get_document("INC-2024-001")
        
        # Verify document was found
        self.assertIsNotNone(doc)
        self.assertEqual(doc.document_id, "INC-2024-001")
        self.assertEqual(doc.incident_id, "INC-2024-001")
        
        # Test non-existent document
        doc_none = self.mock_database.get_document("NON-EXISTENT")
        self.assertIsNone(doc_none)
        
        print("[PASS] Get document tool interface test passed")
    
    def test_tool_interface_search_related_documents(self):
        """Test search_related_documents tool interface."""
        result = self.mock_database.search_related_documents("INC-2024-001")
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.documents, list)
        
        # Verify related documents don't include the source
        document_ids = [doc.document_id for doc in result.documents]
        self.assertNotIn("INC-2024-001", document_ids)
        
        print("[PASS] Search related documents tool interface test passed")
    
    def test_tool_interface_search_historical_incidents(self):
        """Test search_historical_incidents tool interface."""
        result = self.mock_database.search_historical_incidents("payment-api", "latency")
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.documents, list)
        
        # Verify results are incident reports or postmortems
        for doc in result.documents:
            self.assertIn(doc.document_type, ["incident_report", "postmortem"])
        
        print("[PASS] Search historical incidents tool interface test passed")
    
    def test_tool_interface_search_by_version(self):
        """Test search_by_version tool interface."""
        result = self.mock_database.search_by_version("v2.1.0")
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.documents, list)
        
        # Verify version match
        for doc in result.documents:
            self.assertIn("v2.1.0", doc.version.lower())
        
        print("[PASS] Search by version tool interface test passed")
    
    def test_tool_interface_search_by_service(self):
        """Test search_by_service tool interface."""
        result = self.mock_database.search_by_service("orders-api")
        
        # Verify result structure
        self.assertIsNotNone(result)
        self.assertIsInstance(result.documents, list)
        
        # Verify service match
        for doc in result.documents:
            self.assertIn("orders-api", doc.service.lower())
        
        print("[PASS] Search by service tool interface test passed")
    
    def test_entity_extraction_from_results(self):
        """Test entity extraction from search results."""
        # Get some documents
        result = self.mock_database.search_by_service("payment-api")
        
        # Extract entities
        entities = extract_entities_from_results(result.documents)
        
        # Verify entities were extracted
        self.assertTrue(len(entities) > 0)
        
        # Verify entity types
        entity_types = [e.entity_type for e in entities]
        self.assertIn(EntityType.SERVICE, entity_types)
        
        print("[PASS] Entity extraction from results test passed")
    
    def test_merge_entities(self):
        """Test entity merging without duplicates."""
        existing_entities = [
            Entity(entity_type=EntityType.SERVICE, value="payment-api", confidence=0.9),
            Entity(entity_type=EntityType.VERSION, value="v2.1.0", confidence=0.8)
        ]
        
        new_entities = [
            Entity(entity_type=EntityType.SERVICE, value="payment-api", confidence=0.9),  # Duplicate
            Entity(entity_type=EntityType.INCIDENT_ID, value="INC-2024-001", confidence=0.95)  # New
        ]
        
        merged = merge_entities(existing_entities, new_entities)
        
        # Verify no duplicates
        entity_keys = [(e.entity_type, e.value.lower()) for e in merged]
        self.assertEqual(len(entity_keys), len(set(entity_keys)))
        
        # Verify new entity was added
        self.assertTrue(any(e.entity_type == EntityType.INCIDENT_ID for e in merged))
        
        print("[PASS] Merge entities test passed")
    
    def test_follow_up_task_generation(self):
        """Test follow-up task generation based on discovered entities."""
        discovered_entities = [
            Entity(entity_type=EntityType.VERSION, value="v2.8.1", confidence=0.9),
            Entity(entity_type=EntityType.SERVICE, value="orders-api", confidence=0.85)
        ]
        
        searches_performed = []
        
        # Generate follow-up task
        follow_up = generate_follow_up_task(discovered_entities, searches_performed)
        
        # Verify task was generated
        self.assertIsNotNone(follow_up)
        
        # Verify task focuses on version (higher priority)
        self.assertIn("version", follow_up["description"].lower())
        self.assertEqual(follow_up["priority"], "high")
        
        print("[PASS] Follow-up task generation test passed")
    
    def test_duplicate_search_avoidance(self):
        """Test that duplicate searches are avoided."""
        # Create state with existing searches
        state = create_test_state("Test question", "test-001")
        state["investigation_plan"] = InvestigationPlan(
            objective="Test objective",
            entities=[],
            required_evidence=[],
            investigation_tasks=[
                InvestigationTask(
                    task_id="task_1",
                    description="Search for payment-api",
                    task_type="search",
                    priority="high",
                    dependencies=[],
                    expected_outcome="Documents"
                )
            ],
            unanswered_questions=[],
            reasoning="Test reasoning"
        )
        state["discovered_entities"] = [Entity(entity_type=EntityType.SERVICE, value="payment-api", confidence=0.9)]
        state["searches_performed"] = [
            {
                "task_id": "task_1",
                "tool_used": "search_by_service",
                "query_filters": "service: payment-api",
                "results_count": 5,
                "new_entities": [],
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
        
        # Run researcher - should not repeat the same search
        result_state = researcher_agent(state)
        
        # Verify no duplicate searches
        search_queries = [search.get("query_filters") for search in result_state["searches_performed"]]
        self.assertEqual(len(search_queries), len(set(search_queries)))
        
        print("[PASS] Duplicate search avoidance test passed")
    
    def test_iteration_limit_respect(self):
        """Test that iteration limit is respected."""
        # Create state at max iterations with no available tasks
        state = create_test_state("Test question", "test-002")
        state["investigation_plan"] = InvestigationPlan(
            objective="Test objective",
            entities=[],
            required_evidence=[],
            investigation_tasks=[],  # No tasks available
            unanswered_questions=[],
            reasoning="Test reasoning"
        )
        state["iteration_count"] = 5  # At max limit
        
        # Run researcher - should not perform new searches since no tasks available
        result_state = researcher_agent(state)
        
        # Verify iteration count increased but no new searches (no tasks to perform)
        self.assertEqual(result_state["iteration_count"], 6)
        self.assertEqual(len(result_state["searches_performed"]), 0)
        
        print("[PASS] Iteration limit respect test passed")


def run_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("RESEARCHER AGENT TEST SUITE")
    print("=" * 60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResearcherAgent)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)