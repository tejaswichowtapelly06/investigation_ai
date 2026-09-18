"""
Production evidence tool implementation using PostgreSQL.
Implements the EvidenceToolProvider interface with evidence persistence.
"""
import logging
from typing import List, Dict, Any
from app.tools.interfaces import DocumentResult
from app.repositories.postgres_repository import PostgresRepository
from app.tools.analysis_functions import extract_evidence_claims, detect_contradictions, compare_all_incidents

logger = logging.getLogger(__name__)


class ProductionEvidenceTool:
    """Production evidence tool using PostgreSQL for evidence storage and retrieval."""
    
    def __init__(self):
        self._postgres_repo = PostgresRepository()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize repository."""
        if self._initialized:
            return True
        
        try:
            self._postgres_repo.initialize()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize production evidence tool: {e}")
            return False
    
    def extract_evidence(self, documents: List[DocumentResult], investigation_id: str = None) -> List[Dict[str, Any]]:
        """Extract evidence claims from documents and persist to PostgreSQL."""
        if not self._initialized:
            self.initialize()
        
        try:
            # Use analysis_functions for extraction
            claims = extract_evidence_claims(documents)
            
            # Persist to PostgreSQL if available and investigation_id provided
            if investigation_id and self._postgres_repo.is_available():
                for claim in claims:
                    try:
                        self._postgres_repo.save_evidence_claim(
                            investigation_id=investigation_id,
                            document_id=claim.document_id,
                            claim=claim.claim,
                            evidence_type=claim.evidence_type.value,
                            confidence=claim.confidence,
                            metadata=claim.metadata
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store evidence claim: {e}")
            
            return [claim.model_dump() for claim in claims]
        except Exception as e:
            logger.error(f"Error extracting evidence: {e}")
            return []
    
    def detect_contradictions(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """Detect contradictions in documents and persist to PostgreSQL."""
        if not self._initialized:
            self.initialize()
        
        try:
            # Use analysis_functions for detection
            contradictions = detect_contradictions(documents)
            
            # Persist to PostgreSQL if available
            if self._postgres_repo.is_available():
                for contr in contradictions:
                    try:
                        self._postgres_repo.save_contradiction(
                            contradiction_type=contr.contradiction_type,
                            description=contr.description,
                            documents=contr.documents,
                            conflicting_claims=contr.conflicting_claims,
                            resolution=contr.resolution,
                            confidence=contr.confidence
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store contradiction: {e}")
            
            return [contr.model_dump() for contr in contradictions]
        except Exception as e:
            logger.error(f"Error detecting contradictions: {e}")
            return []
    
    def compare_incidents(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]:
        """Compare incidents in documents and persist to PostgreSQL."""
        if not self._initialized:
            self.initialize()
        
        try:
            # Use analysis_functions for comparison
            comparisons = compare_all_incidents(documents)
            
            # Persist to PostgreSQL if available
            if self._postgres_repo.is_available():
                for comp in comparisons:
                    try:
                        self._postgres_repo.save_incident_comparison(
                            current_incident_id=comp.current_incident_id,
                            candidate_incident_id=comp.candidate_incident_id,
                            classification=comp.classification.value,
                            matching_attributes=comp.matching_attributes,
                            differing_attributes=comp.differing_attributes,
                            reasoning=comp.reasoning,
                            confidence=comp.confidence
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store incident relationship: {e}")
            
            return [comp.model_dump() for comp in comparisons]
        except Exception as e:
            logger.error(f"Error comparing incidents: {e}")
            return []
