"""Pydantic request / response schemas for the observability microservice."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class PromptConfig(BaseModel):
    """A single prompt entry inside an ExperimentRequest."""

    prompt: str = Field(..., min_length=1, description="The prompt text to send to the LLM.")
    runs: int = Field(default=1, ge=1, le=50, description="Number of times to run this prompt.")
    validators: List[str] = Field(
        default_factory=list,
        description="Names of validator functions to apply to each output.",
    )
    system_message: Optional[str] = Field(
        default=None, description="Optional system-role message prepended to the request."
    )
    apply_json_normalization: bool = Field(
        default=False,
        description="Strip markdown fences and extract JSON candidate before validation.",
    )
    scenario: Optional[str] = Field(
        default=None, description="Human-readable label for this prompt configuration."
    )


class ExperimentRequest(BaseModel):
    """Body for POST /api/v1/experiments."""

    code: str = Field(default="experiment", description="Experiment identifier used for log grouping.")
    description: Optional[str] = Field(default=None, description="Optional free-text description.")
    prompts: List[PromptConfig] = Field(..., min_length=1, description="One or more prompt configurations.")


# ── Response ──────────────────────────────────────────────────────────────────

class RunResult(BaseModel):
    """Telemetry record for a single LLM call."""

    request_id: str
    trace_id: str
    prompt: str
    output: str
    latency: float
    output_length: int
    status: str
    is_valid: bool
    issues: List[str]


class ExperimentSummary(BaseModel):
    """Aggregated statistics for a completed experiment."""

    total_runs: int
    success_count: int
    valid_count: int
    invalid_count: int
    success_percentage: float
    avg_latency: float
    observed_issue_types: List[str]


class ExperimentResponse(BaseModel):
    """Response body for POST /api/v1/experiments."""

    trace_id: str
    runs: List[Dict[str, Any]]
    summary: ExperimentSummary


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response body for GET /health."""

    service: str = "ai-observability-microservice"
    version: str = "0.1.0"
    status: str = "ok"
