"""
Test helper functions for creating InvestigationState instances.
"""
from datetime import datetime
from app.graph.state import InvestigationState


def create_test_state(question: str = "Test question", investigation_id: str = "test-001") -> InvestigationState:
    """
    Create a default InvestigationState for testing with all required fields.
    """
    return {
        "investigation_id": investigation_id,
        "question": question,
        "investigation_plan": {},
        "entities": [],  # Initial entities from question
        "discovered_entities": [],
        "required_evidence": [],
        "searches_performed": [],
        "retrieved_documents": [],
        "evidence": [],
        "contradictions": [],
        "related_incidents": [],
        "findings": [],
        "evidence_sufficient": False,
        "evidence_gaps": [],
        "evidence_sufficiency_assessment": None,
        "status": "planning",
        "iteration_count": 0,
        "max_iterations": 5,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "investigation_trace": [],
        "final_answer": None,
        "error": None,
        "error_details": None
    }
