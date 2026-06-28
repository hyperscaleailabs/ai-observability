"""
AI Observability Microservice — FastAPI entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

Run via Docker:
    docker build -t ai-observability-svc .
    docker run -p 8000:8000 --env-file .env.local ai-observability-svc
"""
from fastapi import FastAPI

from app.routes import health, experiments

app = FastAPI(
    title="AI Observability Microservice",
    version="0.1.0",
    description=(
        "Production reliability harness for LLM workloads. "
        "Provides structured telemetry, output validation, and controlled recovery "
        "for AI pipelines."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health.router, tags=["health"])
app.include_router(experiments.router, prefix="/api/v1", tags=["experiments"])
