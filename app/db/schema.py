"""
PostgreSQL schema definitions.
"""
from datetime import datetime
from typing import Optional


# SQL schema for creating tables
SCHEMA_SQL = """
-- Documents table: stores document metadata
CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR(255) PRIMARY KEY,
    document_type VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    service VARCHAR(255),
    date DATE,
    version VARCHAR(50),
    content TEXT,
    incident_id VARCHAR(255),
    severity VARCHAR(50),
    author VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Evidence claims table: stores extracted evidence
CREATE TABLE IF NOT EXISTS evidence_claims (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) REFERENCES documents(document_id) ON DELETE CASCADE,
    claim TEXT NOT NULL,
    evidence_type VARCHAR(100) NOT NULL,
    confidence FLOAT DEFAULT 0.8,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Incident relationships table: stores incident comparisons
CREATE TABLE IF NOT EXISTS incident_relationships (
    id SERIAL PRIMARY KEY,
    current_incident_id VARCHAR(255) NOT NULL,
    candidate_incident_id VARCHAR(255) NOT NULL,
    classification VARCHAR(50) NOT NULL,
    matching_attributes TEXT[],
    differing_attributes TEXT[],
    reasoning TEXT,
    confidence FLOAT DEFAULT 0.8,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(current_incident_id, candidate_incident_id)
);

-- Contradictions table: stores detected contradictions
CREATE TABLE IF NOT EXISTS contradictions (
    id SERIAL PRIMARY KEY,
    contradiction_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    documents TEXT[] NOT NULL,
    conflicting_claims TEXT[],
    resolution TEXT,
    confidence FLOAT DEFAULT 0.8,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Investigations table: stores investigation records
CREATE TABLE IF NOT EXISTS investigations (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    investigation_plan JSONB,
    final_answer TEXT,
    evidence_sufficient BOOLEAN DEFAULT FALSE,
    iteration_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_service ON documents(service);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(date);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_incident_id ON documents(incident_id);
CREATE INDEX IF NOT EXISTS idx_documents_version ON documents(version);
CREATE INDEX IF NOT EXISTS idx_evidence_document_id ON evidence_claims(document_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence_claims(evidence_type);
CREATE INDEX IF NOT EXISTS idx_relationships_current ON incident_relationships(current_incident_id);
CREATE INDEX IF NOT EXISTS idx_relationships_candidate ON incident_relationships(candidate_incident_id);
CREATE INDEX IF NOT EXISTS idx_relationships_classification ON incident_relationships(classification);
CREATE INDEX IF NOT EXISTS idx_contradictions_type ON contradictions(contradiction_type);
CREATE INDEX IF NOT EXISTS idx_investigations_created ON investigations(created_at);
"""


def get_schema_sql() -> str:
    """Return the SQL schema for initialization."""
    return SCHEMA_SQL
