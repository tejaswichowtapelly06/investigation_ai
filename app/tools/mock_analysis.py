"""
Mock evidence analysis tools for development/testing.
This implements the EvidenceToolProvider protocol using mock logic.
"""
from typing import List, Dict, Any
from app.tools.interfaces import DocumentResult
from app.tools.analysis_functions import (
    extract_evidence_claims, detect_contradictions, compare_all_incidents
)


class MockEvidenceAnalysis:
    """
    Mock implementation of evidence analysis tools.
    Can be replaced with PostgreSQL-based implementation in production.
    """
    
    def extract_evidence(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """
        Extract evidence claims from documents.
        """
        claims = extract_evidence_claims(documents)
        return [claim.model_dump() for claim in claims]
    
    def detect_contradictions(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """
        Detect contradictions in documents.
        """
        contradictions = detect_contradictions(documents)
        return [contr.model_dump() for contr in contradictions]
    
    def compare_incidents(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """
        Compare incidents in documents.
        """
        comparisons = compare_all_incidents(documents)
        return [comp.model_dump() for comp in comparisons]