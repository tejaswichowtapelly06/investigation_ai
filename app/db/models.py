"""
SQLAlchemy models for PostgreSQL database.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class DocumentType(str, enum.Enum):
    """Document types supported in the system."""
    INCIDENT_REPORT = "incident_report"
    DEPLOYMENT_NOTE = "deployment_note"
    ARCHITECTURE_DOCUMENT = "architecture_document"
    TROUBLESHOOTING_GUIDE = "troubleshooting_guide"
    CUSTOMER_COMPLAINT = "customer_complaint"
    POSTMORTEM = "postmortem"


class EvidenceType(str, enum.Enum):
    """Types of evidence claims."""
    SYMPTOM = "symptom"
    ROOT_CAUSE = "root_cause"
    RESOLUTION = "resolution"
    DEPLOYMENT = "deployment"
    TIMELINE = "timeline"
    SERVICE = "service"
    VERSION = "version"
    ENVIRONMENT = "environment"
    DEPENDENCY = "dependency"
    FAILURE_TYPE = "failure_type"


class RelationshipType(str, enum.Enum):
    """Types of relationships between evidence items."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    SIMILAR_TO = "SIMILAR_TO"
    RELATED_TO = "RELATED_TO"
    SUPERSEDES = "SUPERSEDES"
    PRECEDES = "PRECEDES"


class Document(Base):
    """Document model for storing document metadata and content."""
    __tablename__ = "documents"
    
    document_id = Column(String(255), primary_key=True)
    document_type = Column(SQLEnum(DocumentType), nullable=False, index=True)
    title = Column(Text, nullable=False)
    service = Column(String(255), index=True)
    date = Column(DateTime, index=True)
    version = Column(String(50), index=True)
    content = Column(Text)
    source = Column(String(500))  # Original file path or source
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    evidence = relationship("Evidence", back_populates="document", cascade="all, delete-orphan")
    relationships_as_source = relationship("DocumentRelationship", foreign_keys="DocumentRelationship.source_document_id", back_populates="source_document")
    relationships_as_target = relationship("DocumentRelationship", foreign_keys="DocumentRelationship.target_document_id", back_populates="target_document")


class Evidence(Base):
    """Evidence model for storing extracted evidence claims."""
    __tablename__ = "evidence"
    
    evidence_id = Column(String(255), primary_key=True)
    investigation_id = Column(String(255), ForeignKey("investigations.investigation_id"), nullable=True, index=True)
    document_id = Column(String(255), ForeignKey("documents.document_id"), nullable=False, index=True)
    claim = Column(Text, nullable=False)
    evidence_type = Column(SQLEnum(EvidenceType), nullable=False, index=True)
    confidence = Column(Float, default=0.8)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="evidence")
    investigation = relationship("Investigation", back_populates="evidence")
    relationships_as_source = relationship("EvidenceRelationship", foreign_keys="EvidenceRelationship.source_evidence_id", back_populates="source_evidence")
    relationships_as_target = relationship("EvidenceRelationship", foreign_keys="EvidenceRelationship.target_evidence_id", back_populates="target_evidence")


class EvidenceRelationship(Base):
    """Relationships between evidence items."""
    __tablename__ = "evidence_relationships"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_evidence_id = Column(String(255), ForeignKey("evidence.evidence_id"), nullable=False, index=True)
    target_evidence_id = Column(String(255), ForeignKey("evidence.evidence_id"), nullable=False, index=True)
    relationship_type = Column(SQLEnum(RelationshipType), nullable=False, index=True)
    confidence = Column(Float, default=0.8)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_evidence = relationship("Evidence", foreign_keys=[source_evidence_id], back_populates="relationships_as_source")
    target_evidence = relationship("Evidence", foreign_keys=[target_evidence_id], back_populates="relationships_as_target")


class DocumentRelationship(Base):
    """Relationships between documents."""
    __tablename__ = "document_relationships"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_document_id = Column(String(255), ForeignKey("documents.document_id"), nullable=False, index=True)
    target_document_id = Column(String(255), ForeignKey("documents.document_id"), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False, index=True)  # e.g., "incident_to_deployment", "guide_supersedes"
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_document = relationship("Document", foreign_keys=[source_document_id], back_populates="relationships_as_source")
    target_document = relationship("Document", foreign_keys=[target_document_id], back_populates="relationships_as_target")


class IncidentComparison(Base):
    """Incident comparisons stored in PostgreSQL."""
    __tablename__ = "incident_comparisons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    current_incident_id = Column(String(255), nullable=False, index=True)
    candidate_incident_id = Column(String(255), nullable=False, index=True)
    classification = Column(String(50), nullable=False, index=True)  # SAME, SIMILAR, DIFFERENT, INSUFFICIENT_EVIDENCE
    matching_attributes = Column(JSON, default=list)
    differing_attributes = Column(JSON, default=list)
    reasoning = Column(Text)
    confidence = Column(Float, default=0.8)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Contradiction(Base):
    """Contradictions detected between documents."""
    __tablename__ = "contradictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contradiction_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    documents = Column(JSON, default=list)  # List of document IDs
    conflicting_claims = Column(JSON, default=list)
    resolution = Column(Text)
    confidence = Column(Float, default=0.8)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class Investigation(Base):
    """Investigation records."""
    __tablename__ = "investigations"
    
    investigation_id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    investigation_plan = Column(JSON, default=dict)
    final_answer = Column(Text)
    evidence_sufficient = Column(Integer, default=0)  # 0 or 1 for SQLite compatibility
    iteration_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    evidence = relationship("Evidence", back_populates="investigation", cascade="all, delete-orphan")
    events = relationship("InvestigationEvent", back_populates="investigation", cascade="all, delete-orphan")


class InvestigationEvent(Base):
    """Events during an investigation (for trace)."""
    __tablename__ = "investigation_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    investigation_id = Column(String(255), ForeignKey("investigations.investigation_id"), nullable=False, index=True)
    iteration = Column(Integer, default=0)
    agent = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    investigation = relationship("Investigation", back_populates="events")
