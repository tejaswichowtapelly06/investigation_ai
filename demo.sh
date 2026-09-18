#!/bin/bash

# Demo Script for Investigation AI
# This script demonstrates the best sequence for running the system

set -e

echo "=========================================="
echo "Investigation AI Demo Script"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please configure .env with your settings before running the demo."
    echo "For mock mode (no infrastructure), set USE_MOCK_DATA=true"
    echo "For production mode, set USE_MOCK_DATA=false and configure PostgreSQL/Qdrant"
    exit 1
fi

# Read mode from .env
MODE=$(grep USE_MOCK_DATA .env | cut -d '=' -f2)

echo "Running in mode: $MODE"
echo ""

if [ "$MODE" = "true" ]; then
    echo "=========================================="
    echo "MOCK MODE (No Infrastructure Required)"
    echo "=========================================="
    echo ""
    
    echo "Step 1: Starting FastAPI backend..."
    echo "Run: uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    
    echo "Step 2: Starting Streamlit UI..."
    echo "Run: streamlit run app/ui/app.py"
    echo ""
    
    echo "Step 3: Open browser to http://localhost:8501"
    echo ""
    
    echo "Example question to try:"
    echo "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"
    echo ""
    
else
    echo "=========================================="
    echo "PRODUCTION MODE (Infrastructure Required)"
    echo "=========================================="
    echo ""
    
    echo "Step 1: Starting infrastructure (PostgreSQL + Qdrant)..."
    docker-compose up -d
    echo "Waiting for services to be ready..."
    sleep 10
    echo ""
    
    echo "Step 2: Initializing PostgreSQL database..."
    python -m app.db.init_db
    echo ""
    
    echo "Step 3: Ingesting sample documents..."
    python -m app.ingestion.ingest data/sample_documents.json
    echo ""
    
    echo "Step 4: Starting FastAPI backend..."
    echo "Run: uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    
    echo "Step 5: Starting Streamlit UI..."
    echo "Run: streamlit run app/ui/app.py"
    echo ""
    
    echo "Step 6: Open browser to http://localhost:8501"
    echo ""
    
    echo "Example question to try:"
    echo "Why did the Order API become slow on September 16? Was the deployment related and have we seen this before?"
    echo ""
    
    echo "To stop infrastructure after demo:"
    echo "docker-compose down"
    echo ""
fi

echo "=========================================="
echo "Demo Setup Complete"
echo "=========================================="
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "Streamlit UI: http://localhost:8501"
echo ""
