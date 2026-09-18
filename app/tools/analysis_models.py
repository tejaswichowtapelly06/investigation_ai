"""
Structured models for evidence analysis.
These models provide clean interfaces for evidence claims and incident comparisons.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class EvidenceType(Enum):
    """Types of evidence that can be extracted from documents."""
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
    FACT = "fact"
    CONFIGURATION = "configuration"
    HISTORICAL_PRECEDENT = "historical_precedent"
    TROUBLESHOOTING_GUIDANCE = "troubleshooting_guidance"
    ARCHITECTURE = "architecture"
    RELATIONSHIP = "relationship"


class EvidenceGrade(Enum):
    """Grades for evidence quality and reliability."""
    DIRECT_EVIDENCE = "direct_evidence"
    INFERRED = "inferred"
    CORROBORATED = "corroborated"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class ContradictionType(Enum):
    """Types of contradictions that can be detected."""
    VERSION_CONFLICT = "version_conflict"
    DATE_CONFLICT = "date_conflict"
    ROOT_CAUSE_CONFLICT = "root_cause_conflict"
    GUIDANCE_CONFLICT = "guidance_conflict"
    CONFIGURATION_CONFLICT = "configuration_conflict"
    RELATIONSHIP_CONFLICT = "relationship_conflict"


class DocumentRelationship(Enum):
    """Relationships between documents."""
    SUPERSEDES = "supersedes"
    SUPERSEDED_BY = "superseded_by"
    DEPRECATED = "deprecated"
    REPLACES = "replaces"
    RELATED = "related"
    CONFLICTS = "conflicts"


class Classification(Enum):
    """Classification for incident comparisons."""
    SAME = "SAME"
    SIMILAR = "SIMILAR"
    DIFFERENT = "DIFFERENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CausationType(Enum):
    """Types of causation evidence."""
    DOCUMENTED_CAUSAL = "documented_causal"
    TEMPORAL_ASSOCIATION = "temporal_association"
    NO_EVIDENCE = "no_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceClaim(BaseModel):
    """A specific claim extracted from a document."""
    evidence_id: str = Field(default="", description="Unique identifier for the evidence")
    claim: str = Field(description="The specific claim made in the document")
    source_document_id: str = Field(description="Source document ID")
    source_document_type: str = Field(default="", description="Type of source document")
    source_date: str = Field(default="", description="Date of source document")
    relevant_version: str = Field(default="", description="Relevant version if applicable")
    relevant_service: str = Field(default="", description="Relevant service if applicable")
    related_entity: str = Field(default="", description="Related entity (e.g., deployment_id, incident_id)")
    relationship: str = Field(default="", description="Relationship to the investigation")
    evidence_type: EvidenceType = Field(description="Type of evidence")
    grade: EvidenceGrade = Field(default=EvidenceGrade.UNKNOWN, description="Grade of evidence quality")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the claim")
    supporting_text: str = Field(default="", description="Supporting text/reference from document")
    supports: List[str] = Field(default_factory=list, description="Other claims this supports")
    contradicts: List[str] = Field(default_factory=list, description="Other claims this contradicts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class IncidentAttributes(BaseModel):
    """Attributes extracted from an incident document."""
    service: str = Field(default="", description="Service/component affected")
    symptom: str = Field(default="", description="Symptom or error description")
    cause: str = Field(default="", description="Root cause")
    version: str = Field(default="", description="Version at time of incident")
    dependency: str = Field(default="", description="Dependencies involved")
    failure_type: str = Field(default="", description="Type of failure")
    deployment_context: str = Field(default="", description="Deployment-related context")
    environment: str = Field(default="", description="Environment (prod, staging, etc.)")
    timeline: str = Field(default="", description="Timeline information")
    date: str = Field(default="", description="Incident date")
    incident_id: str = Field(default="", description="Incident identifier")


class IncidentComparison(BaseModel):
    """Structured comparison between two incidents."""
    current_incident_id: str = Field(description="Current incident being investigated")
    candidate_incident_id: str = Field(description="Candidate incident for comparison")
    classification: Classification = Field(description="Classification of the relationship")
    matching_attributes: List[str] = Field(default_factory=list, description="Attributes that match")
    differing_attributes: List[str] = Field(default_factory=list, description="Attributes that differ")
    reasoning: str = Field(default="", description="Explanation of the classification")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the classification")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional comparison details")


class Contradiction(BaseModel):
    """A contradiction detected between documents."""
    contradiction_id: str = Field(default="", description="Unique identifier for the contradiction")
    claim_a: str = Field(description="First conflicting claim")
    source_a: str = Field(description="Source of first claim (document ID)")
    claim_b: str = Field(description="Second conflicting claim")
    source_b: str = Field(description="Source of second claim (document ID)")
    contradiction_type: ContradictionType = Field(description="Type of contradiction")
    description: str = Field(description="Description of the contradiction")
    documents: List[str] = Field(default_factory=list, description="Document IDs involved")
    conflicting_claims: List[str] = Field(default_factory=list, description="The conflicting claims")
    dates: List[str] = Field(default_factory=list, description="Relevant dates")
    versions: List[str] = Field(default_factory=list, description="Relevant versions")
    resolution_status: str = Field(default="unresolved", description="Status of resolution")
    applicable_scope: str = Field(default="", description="Scope where contradiction applies")
    explanation: str = Field(default="", description="Explanation of the contradiction")
    resolution: Optional[str] = Field(default=None, description="Potential resolution if available")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the contradiction")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class CausationAnalysis(BaseModel):
    """Analysis of causal relationship between deployment and incident."""
    deployment_id: str = Field(description="Deployment identifier")
    incident_id: str = Field(description="Incident identifier")
    causation_type: CausationType = Field(description="Type of causal relationship")
    temporal_relationship: str = Field(default="", description="Description of temporal relationship")
    documented_evidence: List[str] = Field(default_factory=list, description="Evidence for causation")
    reasoning: str = Field(default="", description="Explanation of the analysis")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the analysis")


class EvidenceSufficiency(BaseModel):
    """Assessment of evidence sufficiency."""
    is_sufficient: bool = Field(description="Whether evidence is sufficient")
    evidence_gaps: List[str] = Field(default_factory=list, description="Gaps in evidence")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the assessment")
    reasoning: str = Field(default="", description="Explanation of the assessment")
    required_evidence_types: List[EvidenceType] = Field(default_factory=list, description="Evidence types that are required")
    available_evidence_types: List[EvidenceType] = Field(default_factory=list, description="Evidence types that are available")


class TimelineEvent(BaseModel):
    """An event in the investigation timeline."""
    timestamp: str = Field(description="Timestamp of the event")
    event_type: str = Field(description="Type of event (deployment, incident, configuration_change, etc.)")
    entity: str = Field(description="Entity involved (service, deployment_id, incident_id)")
    source: str = Field(description="Source document ID")
    description: str = Field(default="", description="Description of the event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class DocumentRelationship(BaseModel):
    """Relationship between documents."""
    relationship_type: str = Field(description="Type of relationship (SUPERSEDES, SUPERSEDED_BY, DEPRECATED, REPLACES, RELATED, CONFLICTS)")
    source_document_id: str = Field(description="Source document ID")
    target_document_id: str = Field(description="Target document ID")
    explanation: str = Field(default="", description="Explanation of the relationship")
    applicable_version: str = Field(default="", description="Version where this relationship applies")
    applicable_date: str = Field(default="", description="Date where this relationship applies")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")