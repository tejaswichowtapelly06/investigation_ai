# System Architecture

## Overview

Investigation AI is an agentic incident investigation system that uses a multi-agent architecture to analyze incidents, detect contradictions, compare historical incidents, and provide evidence-backed conclusions. The system is designed to be explainable, with full traceability of how conclusions are reached.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI                            │
│                    (app/ui/app.py)                          │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP API
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI                                 │
│                   (app/api/main.py)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Workflow                         │
│                  (app/graph/workflow.py)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
┌──────────────┐ ┌──────────┐ ┌──────────┐
│   Planner    │ │Researcher│ │  Analyst │
│   Agent      │ │  Agent   │ │  Agent   │
└──────────────┘ └──────────┘ └──────────┘
        │              │            │
        └──────────────┴────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   Tool Registry                              │
│              (app/tools/tool_registry.py)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
┌──────────────┐         ┌──────────────┐
│  Search Tool │         │ Evidence Tool│
└──────────────┘         └──────────────┘
        │                         │
        ↓                         ↓
┌──────────────┐         ┌──────────────┐
│  Mock/Prod   │         │  Mock/Prod   │
│  Repository  │         │  Repository  │
└──────────────┘         └──────────────┘
        │                         │
        ↓                         ↓
┌──────────────┐         ┌──────────────┐
│  Qdrant      │         │ PostgreSQL   │
│  (Vector DB) │         │ (Relational) │
└──────────────┘         └──────────────┘
```

## Agent Architecture

### Planner Agent

**Responsibility**: Convert natural-language question into structured investigation plan.

**Inputs**:
- User question
- Discovered entities (from previous iterations, if any)

**Outputs**:
- Investigation plan with objective
- Required evidence types
- Investigation tasks with priorities
- Unanswered questions
- Extracted entities

**Key Behaviors**:
- Extracts entities using regex patterns (service, incident_id, date, version, symptom, deployment, document_type)
- Creates structured plan with evidence-based reasoning
- Does NOT claim facts without evidence
- Sets iteration count to 0

**File**: `app/agents/planner.py`

### Researcher Agent

**Responsibility**: Perform searches based on investigation plan and discovered evidence.

**Inputs**:
- Investigation plan
- Discovered entities
- Searches already performed
- Evidence gaps from previous iteration

**Outputs**:
- New documents retrieved
- New entities discovered
- Updated search history
- Investigation trace entry

**Key Behaviors**:
- Multi-hop investigation: uses discoveries from earlier searches to trigger follow-up searches
- Duplicate avoidance: tracks performed searches and skips duplicates
- Evidence gap addressing: prioritizes searches to fill identified gaps
- Iteration limit respect: stops at max_iterations
- Dependency satisfaction: respects task dependencies

**Multi-hop Logic**:
1. If version discovered → search for deployment
2. If incident_id discovered → search for postmortem
3. If service discovered → search for related incidents
4. If evidence gaps → generate gap-addressing tasks

**File**: `app/agents/researcher.py`

### Analyst Agent

**Responsibility**: Analyze evidence for contradictions, temporal relationships, and sufficiency.

**Inputs**:
- Retrieved documents
- Evidence from previous iterations
- Contradictions from previous iterations
- Investigation plan

**Outputs**:
- Evidence claims
- Contradictions
- Incident comparisons
- Findings
- Evidence sufficiency status
- Evidence gaps
- Investigation trace entry

**Key Behaviors**:
- Extracts evidence claims with document traceability
- Detects contradictions (version conflicts, root cause conflicts, guidance conflicts)
- Compares incidents using multiple attributes
- Evaluates evidence sufficiency
- Distinguishes temporal association from documented causation

**File**: `app/agents/analyst.py`

### Report Generator

**Responsibility**: Synthesize final investigation report.

**Inputs**:
- Question
- Entities
- Evidence
- Contradictions
- Related incidents
- Findings
- Evidence sufficiency status

**Outputs**:
- Final answer
- Investigation trace entry

**Key Behaviors**:
- Generates structured report with evidence backing
- Explicitly states evidence gaps when insufficient
- Includes contradictions and resolutions
- Includes incident comparisons

**File**: `app/graph/workflow.py`

## Database Architecture

### PostgreSQL Schema

**documents**
- `document_id` (PK): Unique identifier
- `document_type` (ENUM): incident_report, deployment_note, postmortem, troubleshooting_guide, architecture_document
- `title`: Document title
- `service`: Service name
- `date`: Date (YYYY-MM-DD)
- `version`: Version string
- `content`: Full document content
- `source`: Source file path
- `metadata` (JSON): Additional metadata
- `created_at`, `updated_at`: Timestamps

**evidence**
- `evidence_id` (PK): Unique identifier
- `investigation_id` (FK): Links to investigation
- `document_id` (FK): Links to document
- `claim`: Evidence claim text
- `evidence_type` (ENUM): SYMPTOM, ROOT_CAUSE, RESOLUTION, DEPLOYMENT, SERVICE, VERSION, FAILURE_TYPE, ENVIRONMENT
- `confidence`: Float 0-1
- `metadata` (JSON): Additional metadata
- `created_at`: Timestamp

**evidence_relationships**
- `id` (PK): Unique identifier
- `source_evidence_id` (FK): Links to evidence
- `target_evidence_id` (FK): Links to evidence
- `relationship_type` (ENUM): SUPPORTS, CONTRADICTS, SIMILAR_TO, CAUSES, PRECEDES
- `confidence`: Float 0-1
- `metadata` (JSON): Additional metadata
- `created_at`: Timestamp

**document_relationships**
- `id` (PK): Unique identifier
- `source_document_id` (FK): Links to document
- `target_document_id` (FK): Links to document
- `relationship_type`: String
- `metadata` (JSON): Additional metadata
- `created_at`: Timestamp

**incident_comparisons**
- `id` (PK): Unique identifier
- `current_incident_id`: Current incident ID
- `candidate_incident_id`: Candidate incident ID
- `classification` (ENUM): SAME, SIMILAR, DIFFERENT, INSUFFICIENT_EVIDENCE
- `matching_attributes` (JSON): List of matching attributes
- `differing_attributes` (JSON): List of differing attributes
- `reasoning`: Explanation
- `confidence`: Float 0-1
- `created_at`: Timestamp

**contradictions**
- `id` (PK): Unique identifier
- `contradiction_type`: String
- `description`: Description
- `documents` (JSON): List of document IDs
- `conflicting_claims` (JSON): List of claims
- `resolution`: Resolution text
- `confidence`: Float 0-1
- `created_at`: Timestamp

**investigations**
- `investigation_id` (PK): Unique identifier
- `question`: Investigation question
- `investigation_plan` (JSON): Investigation plan
- `final_answer`: Final answer
- `evidence_sufficient`: Boolean
- `iteration_count`: Integer
- `created_at`, `completed_at`: Timestamps

**investigation_events**
- `id` (PK): Unique identifier
- `investigation_id` (FK): Links to investigation
- `iteration`: Iteration number
- `agent`: Agent name (planner, researcher, analyst, report)
- `action`: Action performed
- `metadata` (JSON): Additional metadata
- `timestamp`: Timestamp

**File**: `app/db/models.py`

### Qdrant Schema

**Collection**: `document_chunks`

**Vector Configuration**:
- Dimension: 1536 (OpenAI) or 384 (sentence-transformers)
- Distance: COSINE

**Payload Schema**:
- `chunk_id`: Unique chunk identifier
- `content`: Chunk text
- `document_id`: Source document ID
- `document_type`: Document type
- `service`: Service name
- `date`: Date
- `version`: Version
- `chunk_index`: Index within document
- `metadata` (JSON): Additional metadata

**File**: `app/repositories/qdrant_repository.py`

## Investigation Workflow

### Workflow Graph

```
┌──────────┐
│ Planner  │
└────┬─────┘
     │
     ↓
┌──────────┐
│Researcher│
└────┬─────┘
     │
     ↓
┌──────────┐
│ Analyst  │
└────┬─────┘
     │
     ↓
┌──────────────┐
│ Continue?    │
│ (Conditional)│
└────┬─────┬───┘
     │     │
  Yes│     │No
     │     ↓
     │  ┌────────┐
     │  │ Report │
     │  └───┬────┘
     │      │
     └──────┘
          ↓
        END
```

### Conditional Logic

**should_continue_research**:
1. Check if iteration_count >= max_iterations → report
2. Check if evidence_sufficient → report
3. Otherwise → continue research

**File**: `app/graph/workflow.py`

## Memory and State

### InvestigationState

TypedDict containing:
- `investigation_id`: Unique identifier
- `question`: User question
- `investigation_plan`: Structured plan
- `discovered_entities`: List of Entity objects
- `required_evidence`: List of RequiredEvidence objects
- `searches_performed`: List of search records
- `retrieved_documents`: List of DocumentResult objects
- `evidence`: List of evidence claims
- `contradictions`: List of contradictions
- `related_incidents`: List of incident comparisons
- `findings`: List of findings
- `evidence_sufficient`: Boolean
- `evidence_gaps`: List of gap descriptions
- `iteration_count`: Integer
- `max_iterations`: Integer
- `investigation_trace`: List of trace events
- `final_answer`: Final answer string

**File**: `app/graph/state.py`

### State Persistence

- Graph execution state is in-memory (no LangGraph checkpointing)
- Investigation trace events are persisted to PostgreSQL (`investigation_events` table)
- Permanent evidence/documents are stored separately in PostgreSQL
- Investigation results are persisted to PostgreSQL (`investigations` table)

**Limitation**: LangGraph checkpointing is not implemented, so state is lost after graph execution completes.

## Tool Interactions

### Search Tool Interface

```python
class SearchTool:
    def semantic_search(self, query: str, limit: int = 10) -> List[SearchResult]
    def search_by_service(self, service: str, limit: int = 10) -> List[SearchResult]
    def search_by_version(self, version: str, limit: int = 10) -> List[SearchResult]
    def search_by_date_range(self, start_date: str, end_date: str, limit: int = 10) -> List[SearchResult]
    def search_by_document_type(self, doc_type: str, limit: int = 10) -> List[SearchResult]
    def search_historical_incidents(self, service: str, limit: int = 10) -> List[SearchResult]
    def search_related_documents(self, document_id: str, limit: int = 10) -> List[SearchResult]
    def get_document(self, document_id: str) -> Optional[DocumentResult]
```

### Evidence Tool Interface

```python
class EvidenceToolProvider:
    def extract_evidence(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]
    def detect_contradictions(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]
    def compare_incidents(self, documents: List[DocumentResult]) -> List[Dict[str, Any]]
```

**File**: `app/tools/interfaces.py`

## Why This Is Agentic

The system is genuinely agentic because:

1. **Autonomous Decision Making**: Each agent makes decisions based on current state, not fixed rules
2. **Multi-Hop Reasoning**: Researcher uses discoveries from earlier searches to trigger new searches
3. **Conditional Execution**: Workflow branches based on evidence sufficiency
4. **State Persistence**: Agents share state through InvestigationState
5. **Tool Use**: Agents use tools to interact with external systems
6. **Iteration**: System can loop through Researcher → Analyst until evidence is sufficient
7. **Adaptive Planning**: Planner creates investigation plan based on question analysis
8. **Evidence-Based**: Analyst evaluates evidence before concluding

## Incident Identity Comparison

### Semantic Similarity ≠ Incident Identity

The system explicitly distinguishes between semantic similarity and incident identity by using multi-attribute comparison:

**Attributes Compared**:
- Service
- Version
- Symptom
- Cause
- Dependency
- Failure type
- Environment
- Timeline
- Deployment context

**Classification Logic**:
1. **SAME**: Same incident_id OR all critical attributes match
2. **DIFFERENT**: Different service OR different documented cause OR no matching attributes
3. **SIMILAR**: Multiple matching attributes (≥2) with minor differences (≤2)
4. **INSUFFICIENT_EVIDENCE**: Single matching/differing attribute OR no comparable attributes

**Key Design**: The system defaults to DIFFERENT when in doubt, avoiding false positives.

**File**: `app/tools/analysis_functions.py` (compare_incidents, determine_classification)

## Contradiction Handling

### Detection

**Types of Contradictions**:
1. **Version Conflict**: Same service/version with different dates
2. **Root Cause Conflict**: Same incident with different root causes
3. **Guidance Conflict**: Troubleshooting guides with conflicting instructions
4. **Chronological Inconsistency**: Resolution mentioned before incident

### Resolution

- Both sources are retained
- Date/version considered for resolution
- Newer guide preferred when evidence supports it
- Contradictions appear in final answer
- Resolution suggestions provided when available

**File**: `app/tools/analysis_functions.py` (detect_contradictions)

## Insufficient Evidence Handling

### Detection

**Evidence Gaps**:
- Missing required evidence types (SYMPTOM, ROOT_CAUSE)
- Contradictions detected
- Insufficient incident comparisons
- Fewer than 2 documents

### Behavior

- Performs reasonable additional searches
- Addresses evidence gaps in follow-up iterations
- Avoids hallucinating missing facts
- Explicitly states insufficient evidence
- Reports specific evidence gaps
- Generates incomplete report with available findings

**File**: `app/tools/analysis_functions.py` (evaluate_evidence_sufficiency)

## Temporal Reasoning

### Association vs Causation

**Temporal Association**:
- Deployment precedes incident in time
- No explicit causal link documented
- Classification: TEMPORAL_ASSOCIATION

**Documented Causation**:
- Document explicitly mentions causation
- Keywords: "caused", "causation"
- Classification: DOCUMENTED_CAUSAL

**No Evidence**:
- Incident before deployment
- Too much time between deployment and incident
- Classification: NO_EVIDENCE

**Key Design**: The system never assumes causation from temporal association alone.

**File**: `app/tools/analysis_functions.py` (check_temporal_consistency)
