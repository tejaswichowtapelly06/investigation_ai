"""
FastAPI application for investigation system.
"""
import logging
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.graph.workflow import create_investigation_graph
from app.graph.state import InvestigationState
from app.tools.tool_registry import create_default_registry, create_production_registry
from app.config.settings import settings
from app.repositories.postgres_repository import PostgresRepository
from app.repositories.qdrant_repository import QdrantRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Investigation AI API", version="1.0.0")

# Global repositories for health checks
postgres_repo = PostgresRepository()
qdrant_repo = QdrantRepository()


class InvestigateRequest(BaseModel):
    """Request model for investigation."""
    question: str


class InvestigateResponse(BaseModel):
    """Response model for investigation."""
    investigation_id: str
    status: str
    answer: Optional[str] = None
    findings: list = []
    evidence: list = []
    contradictions: list = []
    related_incidents: list = []
    trace: list = []
    evidence_sufficient: bool = False
    evidence_gaps: list = []
    iteration_count: int = 0


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    postgres: str
    qdrant: str
    investigation_id: str


@app.on_event("startup")
async def startup_event():
    """Initialize repositories on startup."""
    try:
        postgres_repo.initialize()
        qdrant_repo.initialize()
        logger.info("Repositories initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize repositories: {e}")


@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    postgres_status = "healthy" if postgres_repo.is_available() else "unhealthy"
    qdrant_status = "healthy" if qdrant_repo.is_available() else "unhealthy"
    
    overall_status = "healthy" if postgres_status == "healthy" and qdrant_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        postgres=postgres_status,
        qdrant=qdrant_status,
        investigation_id=str(uuid.uuid4())
    )


@app.post("/investigate", response_model=InvestigateResponse)
async def investigate(request: InvestigateRequest, background_tasks: BackgroundTasks) -> InvestigateResponse:
    """
    Start an investigation.
    
    This endpoint runs the investigation synchronously for the demo.
    In production, this could be made asynchronous with background tasks.
    """
    investigation_id = str(uuid.uuid4())
    
    try:
        # Select tool registry based on settings
        if settings.USE_MOCK_DATA:
            tool_registry = create_default_registry()
            logger.info("Using mock tool registry")
        else:
            tool_registry = create_production_registry()
            logger.info("Using production tool registry")
        
        # Initialize state
        initial_state: InvestigationState = {
            "investigation_id": investigation_id,
            "question": request.question,
            "investigation_plan": {},
            "discovered_entities": [],
            "required_evidence": [],
            "searches_performed": [],
            "retrieved_documents": [],
            "evidence": [],
            "contradictions": [],
            "related_incidents": [],
            "findings": [],
            "evidence_sufficient": False,
            "evidence_gaps": [],
            "iteration_count": 0,
            "max_iterations": settings.MAX_ITERATIONS,
            "investigation_trace": [],
            "final_answer": None
        }
        
        # Create and run the graph
        graph = create_investigation_graph(tool_registry)
        final_state = graph.invoke(initial_state)
        
        # Persist investigation to PostgreSQL
        if postgres_repo.is_available():
            postgres_repo.save_investigation(
                investigation_id=investigation_id,
                question=request.question,
                investigation_plan=final_state.get("investigation_plan", {}),
                final_answer=final_state.get("final_answer"),
                evidence_sufficient=final_state.get("evidence_sufficient", False),
                iteration_count=final_state.get("iteration_count", 0)
            )
        
        # Build response
        return InvestigateResponse(
            investigation_id=investigation_id,
            status="completed",
            answer=final_state.get("final_answer"),
            findings=final_state.get("findings", []),
            evidence=final_state.get("evidence", []),
            contradictions=final_state.get("contradictions", []),
            related_incidents=final_state.get("related_incidents", []),
            trace=final_state.get("investigation_trace", []),
            evidence_sufficient=final_state.get("evidence_sufficient", False),
            evidence_gaps=final_state.get("evidence_gaps", []),
            iteration_count=final_state.get("iteration_count", 0)
        )
        
    except Exception as e:
        logger.error(f"Error during investigation: {e}")
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(e)}")


@app.get("/investigations/{investigation_id}")
async def get_investigation(investigation_id: str) -> InvestigateResponse:
    """
    Get investigation result by ID.
    
    This retrieves the investigation from PostgreSQL if available.
    """
    if not postgres_repo.is_available():
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable")
    
    try:
        from app.db.models import Investigation
        from sqlalchemy.orm import Session
        
        with Session(postgres_repo._engine) as session:
            investigation = session.query(Investigation).filter_by(investigation_id=investigation_id).first()
            
            if not investigation:
                raise HTTPException(status_code=404, detail="Investigation not found")
            
            # Get investigation events for trace
            from app.db.models import InvestigationEvent
            events = session.query(InvestigationEvent).filter_by(
                investigation_id=investigation_id
            ).order_by(InvestigationEvent.timestamp).all()
            
            trace = []
            for event in events:
                trace.append({
                    "iteration": event.iteration,
                    "agent": event.agent,
                    "action": event.action,
                    "timestamp": event.timestamp.isoformat(),
                    **event.metadata
                })
            
            return InvestigateResponse(
                investigation_id=investigation.investigation_id,
                status="completed" if investigation.completed_at else "incomplete",
                answer=investigation.final_answer,
                findings=[],  # Would need to be stored separately
                evidence=[],  # Would need to be stored separately
                contradictions=[],  # Would need to be stored separately
                related_incidents=[],  # Would need to be stored separately
                trace=trace,
                evidence_sufficient=bool(investigation.evidence_sufficient),
                evidence_gaps=[],  # Would need to be stored separately
                iteration_count=investigation.iteration_count
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving investigation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve investigation: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Investigation AI API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "investigate": "/investigate (POST)",
            "investigations": "/investigations/{investigation_id} (GET)"
        }
    }
