from typing import TypedDict, List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from app.tools.analysis_models import (
    EvidenceClaim, IncidentComparison, Contradiction, EvidenceSufficiency
)


class IncidentComparison(Enum):
    SAME = "SAME"
    SIMILAR = "SIMILAR"
    DIFFERENT = "DIFFERENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class InvestigationStatus(Enum):
    """Status of the investigation lifecycle."""
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EntityType(Enum):
    SERVICE = "service"
    INCIDENT_ID = "incident_id"
    DATE = "date"
    DATE_RANGE = "date_range"
    VERSION = "version"
    SYMPTOM = "symptom"
    ERROR = "error"
    DEPENDENCY = "dependency"
    DEPLOYMENT = "deployment"
    DOCUMENT_TYPE = "document_type"


class Entity(BaseModel):
    """Structured entity extracted from investigation question."""
    entity_type: EntityType
    value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    context: str = Field(default="")


class InvestigationTask(BaseModel):
    """A specific task to be performed during investigation."""
    task_id: str
    description: str
    task_type: str = Field(default="search")  # search, compare, analyze, verify
    priority: str = Field(default="medium")  # high, medium, low
    dependencies: List[str] = Field(default_factory=list)
    expected_outcome: str = Field(default="")


class RequiredEvidence(BaseModel):
    """Specific evidence required to answer the investigation."""
    evidence_type: str
    description: str
    source_suggestions: List[str] = Field(default_factory=list)
    critical: bool = Field(default=False)


class InvestigationPlan(BaseModel):
    """Structured investigation plan created by Planner Agent."""
    objective: str = Field(default="", description="Primary objective of the investigation")
    entities: List[Entity] = Field(default_factory=list, description="Entities identified in the question")
    required_evidence: List[RequiredEvidence] = Field(default_factory=list, description="Evidence needed to answer the question")
    investigation_tasks: List[InvestigationTask] = Field(default_factory=list, description="Specific tasks to perform")
    unanswered_questions: List[str] = Field(default_factory=list, description="Questions that need to be answered")
    reasoning: str = Field(default="", description="Planner's reasoning about the investigation approach")


class InvestigationState(TypedDict):
    """Complete investigation state supporting full lifecycle."""
    # Identification
    investigation_id: str  # Unique identifier for the investigation
    question: str  # Original investigation question
    
    # Planning phase
    investigation_plan: Union[InvestigationPlan, Dict[str, Any]]  # Structured plan from Planner
    entities: List[Entity]  # Entities extracted from question (initial)
    discovered_entities: List[Entity]  # Entities discovered during investigation (cumulative)
    required_evidence: List[RequiredEvidence]  # Evidence required to answer the question
    
    # Research phase
    searches_performed: List[Dict[str, Any]]  # Search history with metadata
    retrieved_documents: List[Dict[str, Any]]  # Documents retrieved (cumulative)
    
    # Analysis phase
    evidence: Union[List[EvidenceClaim], List[Dict[str, Any]]]  # Evidence claims extracted
    contradictions: Union[List[Contradiction], List[Dict[str, Any]]]  # Contradictions detected
    related_incidents: Union[List[IncidentComparison], List[Dict[str, Any]]]  # Incident comparisons
    findings: List[str]  # Key findings from analysis
    
    # Evaluation phase
    evidence_sufficient: bool  # Whether evidence is sufficient to answer
    evidence_gaps: List[str]  # Missing evidence types identified by Analyst
    evidence_sufficiency_assessment: Optional[Union[EvidenceSufficiency, Dict[str, Any]]]  # Detailed sufficiency assessment
    
    # Lifecycle management
    status: Union[InvestigationStatus, str]  # Current status of investigation
    iteration_count: int  # Current iteration number
    max_iterations: int  # Maximum iterations to prevent infinite loops
    started_at: Optional[str]  # ISO timestamp when investigation started
    completed_at: Optional[str]  # ISO timestamp when investigation completed
    
    # Observability
    investigation_trace: List[Dict[str, Any]]  # Structured trace of investigation steps
    
    # Output
    final_answer: Optional[str]  # Final answer from Report Generator
    
    # Error handling
    error: Optional[str]  # Error message if investigation failed
    error_details: Optional[Dict[str, Any]]  # Additional error details