# Hackathon Demo Application - Startup Commands

## Quick Start

### 1. Start Infrastructure (PostgreSQL + Qdrant)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Qdrant on port 6333

### 2. Initialize Database

```bash
python -m app.db.init_db
```

Creates all PostgreSQL tables using SQLAlchemy.

### 3. Ingest Sample Documents

```bash
python -m app.ingestion.ingest data/sample_documents.json
```

This:
- Parses documents from JSON
- Chunks them (500 chars, 50 overlap)
- Generates embeddings (sentence-transformers by default)
- Stores in Qdrant (chunks + embeddings) and PostgreSQL (metadata)

### 4. Start FastAPI Backend

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 5. Start Streamlit Frontend

```bash
streamlit run app/ui/app.py
```

The UI will be available at `http://localhost:8501`

## Configuration

### Using Mock Data (No Infrastructure Required)

Set in `.env`:
```
USE_MOCK_DATA=true
```

Then skip steps 1-3 and start the backend directly.

### Using Production Databases

Set in `.env`:
```
USE_MOCK_DATA=false
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=investigation_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Using OpenAI Embeddings

Set in `.env`:
```
USE_OPENAI_EMBEDDINGS=true
OPENAI_API_KEY=your_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## API Endpoints

### POST /investigate
Start an investigation.

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

Response:
```json
{
  "status": "healthy",
  "postgres": "healthy",
  "qdrant": "healthy",
  "investigation_id": "uuid"
}
```

### GET /investigations/{investigation_id}
Retrieve investigation by ID (placeholder - full implementation pending).

## UI Features

The Streamlit UI provides:

- **Question Input**: Enter investigation questions
- **Investigation Trace**: Step-by-step investigation process (Planner → Researcher → Analyst → Report)
- **Evidence View**: Clickable document IDs with claim details
- **Incident Comparison**: Comparison tables with classification (SAME/SIMILAR/DIFFERENT)
- **Contradiction View**: Conflicting claims with resolution suggestions
- **Timeline**: Chronological display of events
- **Final Report**: Structured summary with evidence backing

## Example Questions

1. "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"
2. "Investigate incident INC-1042"
3. "Are there similar incidents to the catalog API latency?"
4. "What caused the database connection pool exhaustion?"

## Test Scenarios

### TEST A: Incident → Deployment → Historical Incident
- Temporal relationship detection
- Historical incident comparison
- Deployment causation analysis

### TEST B: Contradictory Guidance
- GUIDE-12 vs GUIDE-41
- Date/version resolution
- Conflict detection

### TEST C: Similar ≠ Identical
- INC-300 vs INC-301
- Same service, similar symptoms
- Classification: SIMILAR (not SAME)

### TEST D: Insufficient Evidence
- No documents found
- Explicit gap reporting
- Evidence insufficient status

## Dependencies

All dependencies are in `requirements.txt`:
- FastAPI, uvicorn (API)
- Streamlit (UI)
- SQLAlchemy, psycopg2-binary (PostgreSQL)
- qdrant-client (Vector DB)
- sentence-transformers (Embeddings)
- OpenAI (Optional embeddings)
- LangGraph, LangChain (Agent orchestration)

## Troubleshooting

### PostgreSQL Connection Failed
- Ensure Docker Compose is running
- Check credentials in `.env`

### Qdrant Connection Failed
- Ensure Docker Compose is running
- Check port 6333 is available

### Embedding Generation Failed
- If using OpenAI, check API key
- Falls back to sentence-transformers automatically

### API Timeout
- Investigations may take time with large document sets
- Increase timeout in Streamlit if needed

## Architecture

```
User Question
↓
FastAPI (/investigate)
↓
LangGraph Workflow
├── Planner Agent (entity extraction, planning)
├── Researcher Agent (multi-hop search)
├── Analyst Agent (evidence analysis)
└── Report Generator
↓
PostgreSQL (evidence persistence)
↓
Streamlit UI (investigation trace display)
```

## Observability

Investigation trace includes:
- timestamp
- investigation_id
- agent (planner/researcher/analyst/report)
- action
- tool/query
- result_count
- new_entities
- decision

This enables full debugging of investigation decisions.
