# Production Knowledge Layer Implementation

## Architecture Overview

The agentic investigation system has been extended with a production-ready knowledge layer using Qdrant for vector/semantic retrieval and PostgreSQL for structured metadata and evidence.

### Data Flow

```
Documents
↓
Ingestion Pipeline
├── Parse & Normalize
├── Chunk (with metadata retention)
├── Embed (OpenAI or sentence-transformers)
└── Store
    ├── Qdrant (chunks + embeddings)
    └── PostgreSQL (document metadata)
↓
Investigation
├── Researcher Tools
│   ├── Qdrant semantic search
│   ├── PostgreSQL metadata search
│   └── Hybrid retrieval (semantic + metadata)
└── Evidence Analyst
    └── PostgreSQL evidence/relationships persistence
```

## Database Schema

### PostgreSQL Tables

**documents**
- document_id (PK)
- document_type (enum: incident_report, deployment_note, etc.)
- title, service, date, version
- content, source
- metadata (JSON)
- created_at, updated_at

**evidence**
- evidence_id (PK)
- investigation_id (FK)
- document_id (FK)
- claim, evidence_type, confidence
- metadata (JSON)
- created_at

**evidence_relationships**
- id (PK)
- source_evidence_id (FK)
- target_evidence_id (FK)
- relationship_type (enum: SUPPORTS, CONTRADICTS, etc.)
- confidence, metadata
- created_at

**document_relationships**
- id (PK)
- source_document_id (FK)
- target_document_id (FK)
- relationship_type
- metadata, created_at

**incident_comparisons**
- id (PK)
- current_incident_id, candidate_incident_id
- classification (SAME, SIMILAR, DIFFERENT, INSUFFICIENT_EVIDENCE)
- matching_attributes, differing_attributes (JSON)
- reasoning, confidence
- created_at

**contradictions**
- id (PK)
- contradiction_type, description
- documents (JSON list)
- conflicting_claims (JSON list)
- resolution, confidence
- created_at

**investigations**
- investigation_id (PK)
- question, investigation_plan (JSON)
- final_answer, evidence_sufficient
- iteration_count
- created_at, completed_at

**investigation_events**
- id (PK)
- investigation_id (FK)
- iteration, agent, action
- metadata (JSON)
- timestamp

### Qdrant Collection

**document_chunks**
- Vector dimension: 1536 (OpenAI) or 384 (sentence-transformers)
- Distance: COSINE
- Payload includes:
  - chunk_id, content
  - document_id, document_type
  - service, date, version
  - chunk_index
  - metadata

## Ingestion Flow

1. **Parse**: Load documents from JSON file
2. **Normalize**: Extract metadata fields
3. **Chunk**: Split documents into chunks (500 chars, 50 overlap)
4. **Embed**: Generate embeddings using OpenAI or sentence-transformers
5. **Store**:
   - PostgreSQL: Document metadata
   - Qdrant: Chunks with embeddings

## Retrieval Flow

### Hybrid Retrieval

The Researcher combines semantic relevance with metadata constraints:

```
query: "Order API latency"
filters: service=orders-api, date_range=Sept 15-17, document_type=incident
↓
Qdrant: semantic search with metadata filters
↓
PostgreSQL: enrich results with full document metadata
↓
Return: ranked results with relevance scores
```

### Evidence Persistence

The Analyst persists analysis results to PostgreSQL:

- Evidence claims with investigation_id
- Incident comparisons with classification
- Contradictions with resolution suggestions

## Commands to Run Locally

### 1. Start Infrastructure

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

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Set `USE_MOCK_DATA=false` to use production databases.

### 4. Ingest Documents

```bash
python -m app.ingestion.ingest data/sample_documents.json
```

This:
- Parses documents
- Chunks them
- Generates embeddings
- Stores in Qdrant and PostgreSQL

### 5. Run Investigation

```bash
python -m app.main "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"
```

## Error Handling

The implements graceful degradation:

- **Qdrant unavailable**: Falls back to PostgreSQL metadata search
- **PostgreSQL unavailable**: Returns empty results with warning
- **Embedding failure**: Falls back to metadata search
- **Empty results**: Logged and handled
- **Duplicate documents**: Skipped with warning

## Test Scenarios

### TEST A: Incident → Deployment → Historical Incident
- Question: "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"
- Expected: Finds DEP-882 (deployment), INC-1042 (incident), PM-211 (historical)
- Temporal relationship: Deployment preceded incident
- Historical comparison: Similar but different cause

### TEST B: Contradictory Guidance
- Question: "How should I troubleshoot database connection issues?"
- Expected: Finds GUIDE-12 and GUIDE-41 with conflicting instructions
- Resolution: Prefer newer guide (GUIDE-41)

### TEST C: Similar ≠ Identical
- Question: "Compare INC-300 and INC-301"
- Expected: Both catalog-api incidents with similar symptoms
- Classification: SIMILAR (not SAME) - different occurrences

### TEST D: Insufficient Evidence
- Question: "What caused the payment service outage on January 1, 2025?"
- Expected: No documents found
- Result: Evidence insufficient, explicit gap reported

## Key Features

- **Hybrid Retrieval**: Semantic + metadata filtering
- **Graceful Degradation**: System functions even if databases unavailable
- **Idempotent Ingestion**: Running twice doesn't duplicate records
- **Evidence Persistence**: Analysis results stored in PostgreSQL
- **Configurable Embeddings**: OpenAI or sentence-transformers
- **Chunk-Level Retrieval**: Results trace back to source documents

## Files Created/Modified

### New Files
- `app/db/models.py` - SQLAlchemy models
- `app/db/init_db.py` - Database initialization
- `app/ingestion/__init__.py` - Ingestion module
- `app/ingestion/chunking.py` - Document chunking
- `app/ingestion/embeddings.py` - Embedding generation
- `app/ingestion/ingest.py` - Ingestion pipeline
- `docker-compose.yml` - Infrastructure
- `data/sample_documents.json` - Sample data

### Modified Files
- `app/config/settings.py` - Added OpenAI, chunking settings
- `app/repositories/qdrant_repository.py` - Updated for production
- `app/repositories/postgres_repository.py` - SQLAlchemy implementation
- `app/tools/production_search.py` - Hybrid retrieval
- `app/tools/production_evidence.py` - Evidence persistence
- `requirements.txt` - Added SQLAlchemy, OpenAI dependencies
- `.env.example` - Updated configuration

## Dependencies Added

```
sqlalchemy>=2.0.0
alembic>=1.12.0
openai>=1.0.0
python-dateutil>=2.8.0
```

## Next Steps

1. Start Docker Compose infrastructure
2. Initialize PostgreSQL database
3. Ingest sample documents
4. Run investigations against ingested data
5. Validate against PS scenarios A, B, C, D
