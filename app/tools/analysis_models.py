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
    claim: str = Field(description="The specific claim made in the document")
    document_id: str = Field(description="Source document ID")
    evidence_type: EvidenceType = Field(description="Type of evidence")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the claim")
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
    contradiction_type: str = Field(description="Type of contradiction")
    description: str = Field(description="Description of the contradiction")
    documents: List[str] = Field(default_factory=list, description="Document IDs involved")
    conflicting_claims: List[str] = Field(default_factory=list, description="The conflicting claims")
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