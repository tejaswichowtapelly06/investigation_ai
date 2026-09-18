from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.graph.workflow import run_investigation
from app.models.request import InvestigateRequest
from app.models.response import ContradictionItem, EvidenceItem, HealthResponse, InvestigateResponse

logger = logging.getLogger("investigation")

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/investigate", response_model=InvestigateResponse)
def investigate(request: InvestigateRequest) -> InvestigateResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="`question` must be a non-empty string.")

    try:
        state = run_investigation(question)
    except Exception:
        logger.exception("Investigation failed for question: %s", question)
        raise HTTPException(status_code=500, detail="Investigation failed due to an internal error.")

    evidence = [
        EvidenceItem(
            document_id=e["document_id"],
            title=e.get("title") or "",
            type=e.get("type") or "",
            date=e.get("date"),
            version=e.get("version"),
            content=e.get("content") or "",
        )
        for e in state.get("evidence", [])
    ]

    contradictions = [
        ContradictionItem(title=c["title"], description=c["description"])
        for c in state.get("contradictions", [])
    ]

    return InvestigateResponse(
        answer=state.get("final_answer") or "The investigation did not produce an answer.",
        confidence=state.get("confidence") or "insufficient",
        evidence=evidence,
        contradictions=contradictions,
        trace=state.get("investigation_steps", []),
    )
