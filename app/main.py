from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.storage.chroma import warm_up

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Agentic Incident Investigation API",
    description="Investigates natural-language incident questions over internal operational documents.",
    version="1.0.0",
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def load_embedding_model() -> None:
    """Warm up the local embedding model before accepting investigations."""
    logging.info("Loading embedding model: %s", settings.embedding_model)
    warm_up()
    logging.info("Embedding model loaded")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # The spec requires 400 for invalid requests; FastAPI defaults to 422.
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.get("/")
def root():
    return {"service": "incident-investigation-api", "docs": "/docs", "health": "/health"}


@app.get("/ui", include_in_schema=False)
def ui():
    return FileResponse(Path(__file__).resolve().parent.parent / "index.html")


@app.get("/investigate", include_in_schema=False)
def investigate_page():
    return RedirectResponse(url="/ui")
