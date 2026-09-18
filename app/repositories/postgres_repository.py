"""
PostgreSQL repository for document metadata and evidence data using SQLAlchemy.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import (
    Document, Evidence, EvidenceRelationship, DocumentRelationship,
    IncidentComparison, Contradiction, Investigation, InvestigationEvent,
    DocumentType, EvidenceType, RelationshipType
)
from app.config.settings import settings
from app.tools.interfaces import DocumentResult, SearchFilters

logger = logging.getLogger(__name__)


class PostgresRepository:
    """Repository for PostgreSQL data access using SQLAlchemy."""
    
    def __init__(self):
        self._engine = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize database connection."""
        if self._initialized:
            return True
        
        try:
            self._engine = create_engine(settings.postgres_url, pool_size=settings.POSTGRES_POOL_SIZE)
            
            # Test connection
            with Session(self._engine) as session:
                session.execute("SELECT 1")
            
            logger.info("PostgreSQL repository initialized successfully")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL repository: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if PostgreSQL is available."""
        if self._engine is None:
            return False
        
        try:
            with Session(self._engine) as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL availability check failed: {e}")
            return False
    
    def get_document_by_id(self, document_id: str) -> Optional[DocumentResult]:
        """Retrieve a document by ID."""
        if not self.is_available():
            logger.warning("PostgreSQL unavailable, returning None")
            return None
        
        try:
            with Session(self._engine) as session:
                doc = session.query(Document).filter_by(document_id=document_id).first()
                if doc:
                    return self._model_to_document_result(doc)
                return None
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    def search_by_metadata(self, filters: SearchFilters) -> List[DocumentResult]:
        """Search documents by metadata fields."""
        if not self.is_available():
            logger.warning("PostgreSQL unavailable, returning empty list")
            return []
        
        try:
            with Session(self._engine) as session:
                query = session.query(Document)
                
                if filters.service:
                    query = query.filter(Document.service == filters.service)
                
                if filters.version:
                    query = query.filter(Document.version == filters.version)
                
                if filters.document_type:
                    query = query.filter(Document.document_type == DocumentType(filters.document_type.lower()))
                
                if filters.incident_id:
                    query = query.filter(Document.metadata['incident_id'].astext == filters.incident_id)
                
                if filters.date_range:
                    start_date, end_date = filters.date_range
                    query = query.filter(Document.date.between(start_date, end_date))
                
                results = query.limit(100).all()
                return [self._model_to_document_result(doc) for doc in results]
        except Exception as e:
            logger.error(f"Error searching by metadata: {e}")
            return []
    
    def save_evidence_claim(
        self,
        investigation_id: str,
        document_id: str,
        claim: str,
        evidence_type: str,
        confidence: float = 0.8,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Save an evidence claim to PostgreSQL."""
        if not self.is_available():
            return None
        
        try:
            import uuid
            with Session(self._engine) as session:
                evidence = Evidence(
                    evidence_id=str(uuid.uuid4()),
                    investigation_id=investigation_id,
                    document_id=document_id,
                    claim=claim,
                    evidence_type=EvidenceType(evidence_type.lower()),
                    confidence=confidence,
                    metadata=metadata or {}
                )
                session.add(evidence)
                session.commit()
                return evidence.evidence_id
        except Exception as e:
            logger.error(f"Error saving evidence claim: {e}")
            return None
    
    def save_incident_comparison(
        self,
        current_incident_id: str,
        candidate_incident_id: str,
        classification: str,
        matching_attributes: List[str],
        differing_attributes: List[str],
        reasoning: str,
        confidence: float = 0.8
    ) -> bool:
        """Save an incident comparison to PostgreSQL."""
        if not self.is_available():
            return False
        
        try:
            with Session(self._engine) as session:
                comparison = IncidentComparison(
                    current_incident_id=current_incident_id,
                    candidate_incident_id=candidate_incident_id,
                    classification=classification,
                    matching_attributes=matching_attributes,
                    differing_attributes=differing_attributes,
                    reasoning=reasoning,
                    confidence=confidence
                )
                session.add(comparison)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving incident comparison: {e}")
            return False
    
    def save_contradiction(
        self,
        contradiction_type: str,
        description: str,
        documents: List[str],
        conflicting_claims: List[str],
        resolution: str = None,
        confidence: float = 0.8
    ) -> bool:
        """Save a contradiction to PostgreSQL."""
        if not self.is_available():
            return False
        
        try:
            with Session(self._engine) as session:
                contradiction = Contradiction(
                    contradiction_type=contradiction_type,
                    description=description,
                    documents=documents,
                    conflicting_claims=conflicting_claims,
                    resolution=resolution,
                    confidence=confidence
                )
                session.add(contradiction)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving contradiction: {e}")
            return False
    
    def save_investigation(
        self,
        investigation_id: str,
        question: str,
        investigation_plan: Dict,
        final_answer: str = None,
        evidence_sufficient: bool = False,
        iteration_count: int = 0
    ) -> bool:
        """Save an investigation record to PostgreSQL."""
        if not self.is_available():
            return False
        
        try:
            with Session(self._engine) as session:
                investigation = Investigation(
                    investigation_id=investigation_id,
                    question=question,
                    investigation_plan=investigation_plan,
                    final_answer=final_answer,
                    evidence_sufficient=1 if evidence_sufficient else 0,
                    iteration_count=iteration_count,
                    completed_at=datetime.utcnow() if final_answer else None
                )
                session.merge(investigation)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving investigation: {e}")
            return False
    
    def save_investigation_event(
        self,
        investigation_id: str,
        iteration: int,
        agent: str,
        action: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Save an investigation event for trace."""
        if not self.is_available():
            return False
        
        try:
            with Session(self._engine) as session:
                event = InvestigationEvent(
                    investigation_id=investigation_id,
                    iteration=iteration,
                    agent=agent,
                    action=action,
                    metadata=metadata or {}
                )
                session.add(event)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving investigation event: {e}")
            return False
    
    def get_incident_relationships(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get incident relationships for an incident."""
        if not self.is_available():
            return []
        
        try:
            with Session(self._engine) as session:
                comparisons = session.query(IncidentComparison).filter(
                    or_(
                        IncidentComparison.current_incident_id == incident_id,
                        IncidentComparison.candidate_incident_id == incident_id
                    )
                ).all()
                
                return [comp.__dict__ for comp in comparisons]
        except Exception as e:
            logger.error(f"Error getting incident relationships: {e}")
            return []
    
    def get_contradictions(self) -> List[Dict[str, Any]]:
        """Get all contradictions."""
        if not self.is_available():
            return []
        
        try:
            with Session(self._engine) as session:
                contradictions = session.query(Contradiction).order_by(
                    Contradiction.created_at.desc()
                ).limit(100).all()
                
                return [contr.__dict__ for contr in contradictions]
        except Exception as e:
            logger.error(f"Error getting contradictions: {e}")
            return []
    
    def _model_to_document_result(self, doc: Document) -> DocumentResult:
        """Convert SQLAlchemy model to DocumentResult."""
        return DocumentResult(
            document_id=doc.document_id,
            document_type=doc.document_type.value,
            title=doc.title,
            service=doc.service or "",
            date=doc.date.strftime("%Y-%m-%d") if doc.date else "",
            version=doc.version or "",
            content=doc.content or "",
            relevance_score=0.0,
            metadata=doc.metadata or {},
            incident_id=doc.metadata.get("incident_id", "") if doc.metadata else "",
            severity=doc.metadata.get("severity", "") if doc.metadata else "",
            author=doc.metadata.get("author", "") if doc.metadata else ""
        )
