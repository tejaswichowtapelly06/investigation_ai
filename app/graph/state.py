from typing import TypedDict, List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class IncidentComparison(Enum):
    SAME = "SAME"
    SIMILAR = "SIMILAR"
    DIFFERENT = "DIFFERENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


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
    question: str
    investigation_plan: Union[InvestigationPlan, Dict[str, Any]]  # Structured plan
    discovered_entities: List[Entity]  # Entities discovered during investigation
    searches_performed: List[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    related_incidents: List[Dict[str, Any]]
    findings: List[str]
    evidence_sufficient: bool
    evidence_gaps: List[str]  # Missing evidence types identified by Analyst
    investigation_trace: List[Dict[str, Any]]  # Structured trace of investigation steps
    final_answer: Optional[str]
    iteration_count: int