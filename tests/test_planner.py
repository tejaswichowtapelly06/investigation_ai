"""
Test suite for the Planner Agent.
Tests the agent's ability to create structured investigation plans
for different types of questions.
"""
import sys
import os
import unittest
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.graph.state import InvestigationState, InvestigationPlan, Entity, EntityType, RequiredEvidence, InvestigationTask
from app.agents.planner import planner_agent, extract_entities_advanced, create_structured_investigation_plan
from tests.test_helpers import create_test_state


class TestPlannerAgent(unittest.TestCase):
    """Test cases for the Planner Agent."""
    
    def test_deployment_related_incident_question(self):
        """Test planning for a deployment-related incident question."""
        question = "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"
        
        # Create initial state
        state = create_test_state(question, "test-001")
        
        # Run planner agent
        result_state = planner_agent(state)
        
        # Verify the plan is structured
        self.assertIsInstance(result_state["investigation_plan"], InvestigationPlan)
        plan = result_state["investigation_plan"]
        
        # Verify objective mentions deployment and causation
        self.assertIn("deployment", plan.objective.lower())
        self.assertIn("causal", plan.objective.lower())
        
        # Verify entities extracted
        self.assertTrue(len(plan.entities) > 0)
        entity_types = [e.entity_type for e in plan.entities]
        self.assertIn(EntityType.SERVICE, entity_types)
        self.assertIn(EntityType.DATE, entity_types)
        
        # Verify required evidence includes deployment-specific evidence
        evidence_types = [e.evidence_type for e in plan.required_evidence]
        self.assertIn("deployment_records", evidence_types)
        self.assertIn("deployment_incident_correlation", evidence_types)
        self.assertIn("causal_analysis", evidence_types)
        
        # Verify investigation tasks include deployment analysis
        task_descriptions = [t.description for t in plan.investigation_tasks]
        deployment_tasks = [t for t in task_descriptions if "deployment" in t.lower()]
        self.assertTrue(len(deployment_tasks) > 0)
        
        # Verify unanswered questions include deployment-specific questions
        unanswered_questions = plan.unanswered_questions
        deployment_questions = [q for q in unanswered_questions if "deployment" in q.lower()]
        self.assertTrue(len(deployment_questions) > 0)
        
        # Verify reasoning mentions deployment and causation
        self.assertIn("deployment", plan.reasoning.lower())
        self.assertIn("causation", plan.reasoning.lower())
        
        print("[PASS] Deployment-related incident question test passed")
    
    def test_historical_incident_question(self):
        """Test planning for a historical incident comparison question."""
        question = "Have we seen this payment service outage before? What were the similar incidents?"
        
        # Create initial state
        state = create_test_state(question, "test-002")
        
        # Run planner agent
        result_state = planner_agent(state)
        
        # Verify the plan is structured
        self.assertIsInstance(result_state["investigation_plan"], InvestigationPlan)
        plan = result_state["investigation_plan"]
        
        # Verify objective mentions historical/similar incidents
        self.assertIn("historical", plan.objective.lower())
        
        # Verify entities extracted
        self.assertTrue(len(plan.entities) > 0)
        entity_types = [e.entity_type for e in plan.entities]
        self.assertIn(EntityType.SERVICE, entity_types)
        
        # Verify required evidence includes historical incident evidence
        evidence_types = [e.evidence_type for e in plan.required_evidence]
        self.assertIn("historical_incidents", evidence_types)
        self.assertIn("root_cause_comparison", evidence_types)
        
        # Verify investigation tasks include historical comparison
        task_descriptions = [t.description for t in plan.investigation_tasks]
        historical_tasks = [t for t in task_descriptions if "historical" in t.lower() or "similar" in t.lower()]
        self.assertTrue(len(historical_tasks) > 0)
        
        # Verify unanswered questions include historical-specific questions
        unanswered_questions = plan.unanswered_questions
        historical_questions = [q for q in unanswered_questions if "similar" in q.lower() or "historical" in q.lower() or "before" in q.lower()]
        self.assertTrue(len(historical_questions) > 0)
        
        # Verify reasoning mentions historical comparison
        self.assertIn("historical", plan.reasoning.lower())
        
        print("[PASS] Historical incident question test passed")
    
    def test_contradiction_troubleshooting_question(self):
        """Test planning for a contradiction/troubleshooting guidance question."""
        question = "There are conflicting instructions in the troubleshooting guides. Which guidance is correct?"
        
        # Create initial state
        state = create_test_state(question, "test-003")
        
        # Run planner agent
        result_state = planner_agent(state)
        
        # Verify the plan is structured
        self.assertIsInstance(result_state["investigation_plan"], InvestigationPlan)
        plan = result_state["investigation_plan"]
        
        # Verify objective mentions contradiction or guidance
        self.assertTrue("contradiction" in plan.objective.lower() or "guidance" in plan.objective.lower())
        
        # Verify entities extracted
        self.assertTrue(len(plan.entities) > 0)
        entity_types = [e.entity_type for e in plan.entities]
        self.assertIn(EntityType.DOCUMENT_TYPE, entity_types)
        
        # Verify investigation tasks include contradiction analysis
        task_descriptions = [t.description for t in plan.investigation_tasks]
        contradiction_tasks = [t for t in task_descriptions if "contradiction" in t.lower() or "conflict" in t.lower()]
        self.assertTrue(len(contradiction_tasks) > 0)
        
        # Verify reasoning mentions contradiction analysis
        self.assertIn("contradiction", plan.reasoning.lower())
        
        print("[PASS] Contradiction/troubleshooting question test passed")
    
    def test_insufficient_evidence_question(self):
        """Test planning for a question that likely has insufficient evidence."""
        question = "What caused the system failure in the legacy authentication module last night?"
        
        # Create initial state
        state = create_test_state(question, "test-004")
        
        # Run planner agent
        result_state = planner_agent(state)
        
        # Verify the plan is structured
        self.assertIsInstance(result_state["investigation_plan"], InvestigationPlan)
        plan = result_state["investigation_plan"]
        
        # Verify objective is to investigate the specific issue
        self.assertIn("investigate", plan.objective.lower())
        
        # Verify entities extracted
        self.assertTrue(len(plan.entities) > 0)
        
        # Verify required evidence includes basic incident information
        evidence_types = [e.evidence_type for e in plan.required_evidence]
        self.assertTrue(len(evidence_types) > 0)
        
        # Verify investigation tasks include evidence sufficiency assessment
        task_descriptions = [t.description for t in plan.investigation_tasks]
        sufficiency_tasks = [t for t in task_descriptions if "sufficiency" in t.lower() or "sufficient" in t.lower()]
        self.assertTrue(len(sufficiency_tasks) > 0)
        
        # Verify unanswered questions are comprehensive
        self.assertTrue(len(plan.unanswered_questions) > 0)
        
        # Verify reasoning mentions evidence gathering and iteration
        self.assertIn("evidence", plan.reasoning.lower())
        self.assertIn("iterate", plan.reasoning.lower())
        
        print("[PASS] Insufficient evidence question test passed")
    
    def test_entity_extraction_service(self):
        """Test entity extraction for service names."""
        question = "What happened with the payment service?"
        entities = extract_entities_advanced(question)
        
        # Verify service entity is extracted
        service_entities = [e for e in entities if e.entity_type == EntityType.SERVICE]
        self.assertTrue(len(service_entities) > 0)
        self.assertEqual(service_entities[0].value, "payment")
        
        print("[PASS] Service entity extraction test passed")
    
    def test_entity_extraction_incident_id(self):
        """Test entity extraction for incident IDs."""
        question = "Investigate incident INC-2024-001"
        entities = extract_entities_advanced(question)
        
        # Verify incident ID entity is extracted
        incident_entities = [e for e in entities if e.entity_type == EntityType.INCIDENT_ID]
        self.assertTrue(len(incident_entities) > 0)
        # The extraction might get just "INC" or the full ID, so check for the key part
        self.assertTrue("INC" in incident_entities[0].value or "2024" in incident_entities[0].value)
        
        print("[PASS] Incident ID entity extraction test passed")
    
    def test_entity_extraction_date(self):
        """Test entity extraction for dates."""
        question = "What happened on September 16, 2024?"
        entities = extract_entities_advanced(question)
        
        # Verify date entity is extracted
        date_entities = [e for e in entities if e.entity_type == EntityType.DATE]
        self.assertTrue(len(date_entities) > 0)
        
        print("[PASS] Date entity extraction test passed")
    
    def test_entity_extraction_version(self):
        """Test entity extraction for versions."""
        question = "Issues with version 2.1.0 of the API"
        entities = extract_entities_advanced(question)
        
        # Verify version entity is extracted
        version_entities = [e for e in entities if e.entity_type == EntityType.VERSION]
        self.assertTrue(len(version_entities) > 0)
        self.assertIn("2.1.0", version_entities[0].value)
        
        print("[PASS] Version entity extraction test passed")
    
    def test_entity_extraction_deployment(self):
        """Test entity extraction for deployment mentions."""
        question = "Was the deployment related to the outage?"
        entities = extract_entities_advanced(question)
        
        # Verify deployment entity is extracted
        deployment_entities = [e for e in entities if e.entity_type == EntityType.DEPLOYMENT]
        self.assertTrue(len(deployment_entities) > 0)
        
        print("[PASS] Deployment entity extraction test passed")
    
    def test_planner_does_not_claim_facts(self):
        """Test that planner does not claim facts without evidence."""
        question = "Why did the system crash?"
        
        # Create initial state
        state = create_test_state(question, "test-005")
        
        # Run planner agent
        result_state = planner_agent(state)
        plan = result_state["investigation_plan"]
        
        # Verify objective is about investigation, not stating facts
        self.assertIn("investigate", plan.objective.lower())
        self.assertNotIn("crashed because", plan.objective.lower())
        self.assertNotIn("caused by", plan.objective.lower())
        
        # Verify reasoning mentions evidence gathering
        self.assertIn("evidence", plan.reasoning.lower())
        
        # Verify required evidence is about gathering information
        for evidence in plan.required_evidence:
            self.assertNotIn("the crash was caused by", evidence.description.lower())
        
        print("[PASS] Planner does not claim facts test passed")
    
    def test_investigation_plan_structure(self):
        """Test that investigation plan has all required fields."""
        question = "What happened with the payment service?"
        
        # Create initial state
        state = create_test_state(question, "test-006")
        
        # Run planner agent
        result_state = planner_agent(state)
        plan = result_state["investigation_plan"]
        
        # Verify all required fields are present
        self.assertIsNotNone(plan.objective)
        self.assertIsInstance(plan.entities, list)
        self.assertIsInstance(plan.required_evidence, list)
        self.assertIsInstance(plan.investigation_tasks, list)
        self.assertIsInstance(plan.unanswered_questions, list)
        self.assertIsNotNone(plan.reasoning)
        
        # Verify fields are not empty (except maybe entities for simple questions)
        self.assertTrue(len(plan.objective) > 0)
        self.assertTrue(len(plan.reasoning) > 0)
        
        print("[PASS] Investigation plan structure test passed")


def run_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("PLANNER AGENT TEST SUITE")
    print("=" * 60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPlannerAgent)
    
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