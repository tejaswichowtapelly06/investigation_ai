from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # The spec requires 400 for invalid requests; FastAPI defaults to 422.
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.get("/")
def root():
    return {"service": "incident-investigation-api", "docs": "/docs", "health": "/health"}
