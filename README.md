# Investigation AI

An agentic incident investigation system that uses multi-agent reasoning to analyze incidents, detect contradictions, compare historical incidents, and provide evidence-backed conclusions.

## Overview

Investigation AI is a multi-agent system that investigates incidents by:
- Extracting entities from natural language questions
- Performing multi-hop searches using semantic and metadata filters
- Analyzing evidence for contradictions and temporal relationships
- Comparing incidents across multiple attributes (not just semantic similarity)
- Distinguishing between temporal association and documented causation
- Explicitly stating when evidence is insufficient

## Architecture

### Agent Architecture

The system follows a strict Planner → Researcher → Analyst → Report workflow:

```
Planner Agent
  ↓
Researcher Agent
  ↓
Analyst Agent
  ↓
[Conditional: Continue Research?]
  ↓ Yes → Researcher Agent
  ↓ No
Report Generator
```

**Planner Agent**
- Extracts entities (service, incident_id, date, version, symptom, deployment, document_type)
- Creates structured investigation plan with objective and required evidence
- Does NOT claim facts without evidence

**Researcher Agent**
- Performs searches based on investigation plan
- Uses discovered entities to trigger follow-up searches (multi-hop)
- Avoids duplicate searches
- Respects iteration limits

**Analyst Agent**
- Extracts evidence claims from documents
- Detects contradictions (version conflicts, root cause conflicts, guidance conflicts)
- Compares incidents using multiple attributes
- Evaluates evidence sufficiency
- Distinguishes temporal association from documented causation

**Report Generator**
- Synthesizes final investigation report
- Includes evidence, contradictions, related incidents
- Explicitly states evidence gaps when insufficient

### Database Architecture

**PostgreSQL** (Structured metadata and evidence)
- `documents`: Document metadata (document_id, type, title, service, date, version, content, source, metadata)
- `evidence`: Evidence claims linked to investigations (evidence_id, investigation_id, document_id, claim, type, confidence)
- `evidence_relationships`: Relationships between evidence (SUPPORTS, CONTRADICTS, SIMILAR_TO, etc.)
- `document_relationships`: Relationships between documents
- `incident_comparisons`: Stored incident comparisons with classification
- `contradictions`: Detected contradictions with resolution
- `investigations`: Investigation records with plans and results
- `investigation_events`: Investigation trace events

**Qdrant** (Vector embeddings for semantic search)
- Collection: `document_chunks`
- Vector dimension: 1536 (OpenAI) or 384 (sentence-transformers)
- Distance: COSINE
- Payload: chunk_id, content, document_id, document_type, service, date, version, chunk_index, metadata

### State and Checkpointing

The system uses LangGraph for orchestration:
- State is passed between agents via `InvestigationState` TypedDict
- Investigation trace events are persisted to PostgreSQL
- Permanent evidence/documents are stored separately from graph execution state
- Note: LangGraph checkpointing is not currently implemented (state is in-memory)

## Tools

### Search Tools

**MockSearchDatabase** (for testing)
- In-memory document store
- Semantic search (mock)
- Metadata search (service, version, date, document_type)
- Related document search
- Historical incident search

**ProductionSearchTool** (for production)
- Qdrant for semantic search with metadata filters
- PostgreSQL for metadata enrichment
- Hybrid retrieval combining both

### Evidence Tools

**MockEvidenceAnalysis** (for testing)
- Delegates to core analysis functions
- Evidence extraction, contradiction detection, incident comparison

**ProductionEvidenceTool** (for production)
- Persists evidence claims to PostgreSQL
- Stores contradictions with resolution
- Stores incident comparisons

## Ingestion

Document ingestion pipeline:
1. Parse documents from JSON
2. Normalize and extract metadata
3. Chunk documents (500 chars, 50 overlap)
4. Generate embeddings (OpenAI or sentence-transformers)
5. Store in Qdrant (chunks + embeddings) and PostgreSQL (metadata)

## Setup

### Prerequisites

- Python 3.8+
- Docker (for PostgreSQL and Qdrant)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create `.env` file:

```bash
# Mode
USE_MOCK_DATA=true  # Set to false for production databases

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=investigation_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=document_chunks
QDRANT_API_KEY=

# OpenAI (optional)
USE_OPENAI_EMBEDDINGS=false
OPENAI_API_KEY=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSION=1536

# Embedding fallback
SENTENCE_TRANSFORMERS_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Ingestion
INGESTION_BATCH_SIZE=10

# Investigation
MAX_ITERATIONS=3
```

## Startup Commands

### Mock Mode (No Infrastructure)

```bash
# Start backend
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Start UI
streamlit run app/ui/app.py
```

### Production Mode (With Infrastructure)

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Initialize database
python -m app.db.init_db

# 3. Ingest sample documents
python -m app.ingestion.ingest data/sample_documents.json

# 4. Start backend
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start UI
streamlit run app/ui/app.py
```

## Test Commands

```bash
# Run all tests
python -m unittest discover tests/ -v

# Run specific test file
python -m unittest tests.test_analyst -v
python -m unittest tests.test_planner -v
python -m unittest tests.test_researcher -v
```

## Example Investigation

**Question**: "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"

**Investigation Trace**:
1. **Planner**: Extracts entities (service=orders-api, date=2024-09-16, deployment mentioned)
2. **Researcher**: Semantic search for "Order API latency September 16"
3. **Discovery**: INC-1042 (incident report), DEP-882 (deployment note)
4. **Researcher**: Version search for v2.8.1
5. **Discovery**: PM-211 (historical postmortem)
6. **Analyst**: Temporal analysis - deployment precedes incident (TEMPORAL_ASSOCIATION)
7. **Analyst**: Incident comparison - similar but different cause (SIMILAR)
8. **Analyst**: Evidence sufficient
9. **Report**: Generated with evidence, timeline, contradictions

## Key Features

### Incident Identity (Not Semantic Similarity)

Incident comparison considers:
- Service
- Symptom
- Cause
- Version
- Dependency
- Failure type
- Environment
- Timeline
- Deployment context

Classification: SAME, SIMILAR, DIFFERENT, INSUFFICIENT_EVIDENCE

**Important**: Similar incidents are NOT incorrectly classified as SAME.

### Contradiction Handling

- Version conflicts detected
- Root cause conflicts detected
- Troubleshooting guide conflicts detected
- Date/version considered for resolution
- Both sources retained
- Appears in final answer

### Temporal Reasoning

Distinguishes:
- "Deployment happened before incident" (TEMPORAL_ASSOCIATION)
- "Deployment caused incident" (DOCUMENTED_CAUSAL)

Only states causation when explicitly documented.

### Insufficient Evidence

- Performs reasonable additional searches
- Avoids hallucinating missing facts
- Explicitly states insufficient evidence
- Reports evidence gaps

### Source Traceability

Every claim maps back to:
- Evidence claim
- Document ID
- Document metadata
- Original document

## Test Scenarios

### TEST A: Temporal vs Causation
- Current incident and deployment are temporally related
- No document explicitly proves causation
- Expected: TEMPORAL_ASSOCIATION, not DOCUMENTED_CAUSAL

### TEST B: Contradictory Guidance
- Two troubleshooting guides give conflicting instructions
- One is newer
- Expected: Contradiction detected, newer guide preferred

### TEST C: Similar ≠ Identical
- INC-300 and INC-301 have similar symptoms
- Different services/causes
- Expected: SIMILAR, not SAME

### TEST D: Insufficient Evidence
- No documents found
- Expected: Explicit insufficient evidence statement

## API Endpoints

### POST /investigate
Start investigation.

Request:
```json
{
  "question": "Why did the Order API become slow on September 16?"
}
```

Response:
```json
{
  "investigation_id": "uuid",
  "status": "completed",
  "answer": "...",
  "findings": [],
  "evidence": [],
  "contradictions": [],
  "related_incidents": [],
  "trace": [],
  "evidence_sufficient": true,
  "evidence_gaps": [],
  "iteration_count": 2
}
```

### GET /health
Health check for all services.

### GET /investigations/{investigation_id}
Retrieve investigation by ID.

## Known Limitations

1. **LangGraph Checkpointing**: Not implemented - state is in-memory
2. **LLM Integration**: Currently uses deterministic analysis functions, not LLM calls
3. **GET /investigations/{id}**: Partially implemented - returns investigation and trace, but not full evidence/contradictions
4. **Real-time Updates**: UI polls API, no WebSocket support
5. **Document Ingestion**: Only supports JSON format
6. **Embedding Model**: Falls back to sentence-transformers if OpenAI unavailable

## Dependencies

- langgraph>=0.0.20
- langchain>=0.1.0
- langchain-core>=0.1.0
- pydantic>=2.0.0
- python-dotenv>=1.0.0
- psycopg2-binary>=2.9.0
- qdrant-client>=1.7.0
- sentence-transformers>=2.2.0
- sqlalchemy>=2.0.0
- alembic>=1.12.0
- openai>=1.0.0
- python-dateutil>=2.8.0
- fastapi>=0.104.0
- uvicorn>=0.24.0
- pydantic-settings>=2.0.0
- streamlit>=1.28.0
- requests>=2.31.0

## License

MIT
