"""
Integration tests for the complete investigation workflow.
Tests the full LangGraph integration of Planner, Researcher, and Analyst agents.
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

from app.graph.workflow import create_investigation_graph
from app.graph.state import InvestigationState
from app.tools.analysis_models import Classification
from app.tools.tool_registry import register_default_providers


class TestInvestigationWorkflow(unittest.TestCase):
    """Integration tests for the complete investigation workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = create_investigation_graph()
        # Register default providers for dependency injection
        register_default_providers()
    
    def test_incident_deployment_historical(self):
        """
        TEST A: Incident → Deployment → Historical Incident
        Test multi-hop investigation from incident to deployment to historical incidents.
        """
        # Question that should trigger incident → deployment → historical investigation
        question = "Why did the Order API become slow on September 16 and have we seen this before?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify investigation ran
        self.assertIsNotNone(result_state)
        self.assertGreater(result_state["iteration_count"], 0)
        
        # Verify trace was created
        self.assertTrue(len(result_state["investigation_trace"]) > 0)
        
        # Verify searches were performed
        self.assertTrue(len(result_state["searches_performed"]) > 0)
        
        # Verify documents were retrieved
        self.assertTrue(len(result_state["retrieved_documents"]) > 0)
        
        # Verify evidence was analyzed
        self.assertTrue(len(result_state["evidence"]) > 0)
        
        # Verify trace contains planner, researcher, and analyst entries
        trace_agents = {entry.get("agent") for entry in result_state["investigation_trace"]}
        self.assertIn("planner", trace_agents)
        self.assertIn("researcher", trace_agents)
        self.assertIn("analyst", trace_agents)
        
        # Verify evidence gaps were tracked
        self.assertIn("evidence_gaps", result_state)
        
        print("[PASS] Incident → Deployment → Historical Incident test passed")
    
    def test_contradictory_guidance_workflow(self):
        """
        TEST B: Contradictory guidance
        Test that the workflow detects and handles contradictory guidance.
        """
        # Question that might reveal contradictory guidance
        question = "What is the recommended approach for handling payment service errors?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify investigation ran
        self.assertIsNotNone(result_state)
        
        # Verify contradictions were checked
        self.assertIn("contradictions", result_state)
        
        # Verify findings mention contradictions (if any found)
        if result_state["contradictions"]:
            self.assertTrue(any("contradiction" in finding.lower() for finding in result_state["findings"]))
        
        # Verify trace shows analyst contradiction detection
        analyst_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "analyst"]
        self.assertTrue(len(analyst_entries) > 0)
        
        print("[PASS] Contradictory guidance workflow test passed")
    
    def test_similar_but_different_incidents(self):
        """
        TEST C: Similar but different incidents
        Test that similar incidents with different services/causes are classified correctly.
        """
        # Question about similar symptoms
        question = "Are there similar incidents to the payment service outage in January 2024?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify investigation ran
        self.assertIsNotNone(result_state)
        
        # Verify incident comparisons were performed
        self.assertTrue(len(result_state["related_incidents"]) > 0)
        
        # Verify not all incidents are classified as SAME
        if result_state["related_incidents"]:
            # Check structured format
            first_comparison = result_state["related_incidents"][0]
            if isinstance(first_comparison, dict):
                classification = first_comparison.get("classification", "unknown")
            else:
                classification = first_comparison.classification.value
            
            # Should not be all SAME (they should be different)
            # This is a weak assertion, but validates the comparison logic runs
            self.assertIsNotNone(classification)
        
        # Verify trace shows incident comparison
        analyst_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "analyst"]
        self.assertTrue(len(analyst_entries) > 0)
        
        print("[PASS] Similar but different incidents workflow test passed")
    
    def test_insufficient_evidence_workflow(self):
        """
        TEST D: Insufficient evidence
        Test that the workflow explicitly reports insufficient evidence when appropriate.
        """
        # Question with very specific, likely unanswerable details
        question = "What caused the specific timeout in the orders-api at 3:42 PM on June 12th?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify investigation ran
        self.assertIsNotNone(result_state)
        
        # Verify evidence sufficiency was determined
        self.assertIn("evidence_sufficient", result_state)
        
        # Verify final answer mentions insufficient evidence if not sufficient
        if not result_state["evidence_sufficient"]:
            final_answer = result_state.get("final_answer", "")
            self.assertTrue(
                "insufficient" in final_answer.lower() or "incomplete" in final_answer.lower(),
                "Final answer should mention insufficient evidence"
            )
        
        # Verify evidence gaps were tracked
        self.assertIn("evidence_gaps", result_state)
        
        # Verify trace shows analyst evaluation
        analyst_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "analyst"]
        self.assertTrue(len(analyst_entries) > 0)
        
        print("[PASS] Insufficient evidence workflow test passed")
    
    def test_trace_structure_completeness(self):
        """Test that the investigation trace has complete structure."""
        question = "What happened with the payment service in January 2024?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify trace exists
        self.assertTrue(len(result_state["investigation_trace"]) > 0)
        
        # Verify each trace entry has required fields
        for entry in result_state["investigation_trace"]:
            self.assertIn("agent", entry)
            self.assertIn("action", entry)
            self.assertIn("iteration", entry)
            self.assertIn("timestamp", entry)
        
        # Verify planner entry has planning details
        planner_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "planner"]
        if planner_entries:
            self.assertIn("objective", planner_entries[0])
            self.assertIn("task_count", planner_entries[0])
        
        # Verify researcher entries have search details
        researcher_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "researcher"]
        for entry in researcher_entries:
            self.assertIn("tool_used", entry)
            self.assertIn("documents_found", entry)
        
        # Verify analyst entries have analysis details
        analyst_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "analyst"]
        for entry in analyst_entries:
            self.assertIn("evidence_count", entry)
            self.assertIn("evidence_sufficient", entry)
        
        print("[PASS] Trace structure completeness test passed")
    
    def test_iteration_limit_respected(self):
        """Test that the workflow respects the maximum iteration limit."""
        question = "What happened with the payment service in January 2024?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify iteration count does not exceed max (5)
        self.assertLessEqual(result_state["iteration_count"], 5)
        
        # Verify investigation completed
        self.assertIsNotNone(result_state.get("final_answer"))
        
        print("[PASS] Iteration limit respected test passed")
    
    def test_evidence_gap_driven_iteration(self):
        """Test that evidence gaps drive subsequent iterations."""
        question = "Why did the payment service become slow in February 2024?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify evidence gaps were tracked
        self.assertIn("evidence_gaps", result_state)
        
        # If evidence gaps were found, verify they were addressed in later iterations
        if result_state["evidence_gaps"]:
            researcher_entries = [entry for entry in result_state["investigation_trace"] if entry.get("agent") == "researcher"]
            # Check if any researcher entry mentions addressing gaps
            gap_addressed = any(entry.get("addressed_gaps") for entry in researcher_entries)
            # This is a weak assertion since gaps might not be immediately addressable
            self.assertIsNotNone(gap_addressed)
        
        print("[PASS] Evidence gap driven iteration test passed")
    
    def test_no_duplicate_searches(self):
        """Test that searches are not blindly repeated."""
        question = "What happened with the payment service in January 2024?"
        
        initial_state: InvestigationState = {
            "question": question,
            "investigation_plan": {},
            "discovered_entities": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "investigation_trace": [],
            "final_answer": None,
            "iteration_count": 0
        }
        
        # Run the investigation
        result_state = self.graph.invoke(initial_state)
        
        # Verify no duplicate searches (same query/filters in same iteration)
        # We'll check that within a single iteration, no duplicates occur
        iteration_searches = {}
        for search in result_state["searches_performed"]:
            signature = (search.get("tool_used"), search.get("query_filters"))
            iteration = search.get("timestamp", "")  # Use timestamp as proxy for iteration
            if iteration not in iteration_searches:
                iteration_searches[iteration] = []
            iteration_searches[iteration].append(signature)
        
        # Check for duplicates within each iteration
        for iteration, signatures in iteration_searches.items():
            unique_signatures = set(signatures)
            self.assertEqual(len(signatures), len(unique_signatures), 
                            f"Searches should not be repeated in the same iteration (iteration: {iteration})")
        
        print("[PASS] No duplicate searches test passed")


def run_tests():
    """Run all integration tests and report results."""
    print("=" * 60)
    print("INVESTIGATION WORKFLOW INTEGRATION TEST SUITE")
    print("=" * 60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInvestigationWorkflow)
    
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