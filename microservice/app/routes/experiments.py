"""
Experiment endpoint — POST /api/v1/experiments.

This module is a scaffold. The LLM integration is marked with TODO comments
showing where the instrument layer (or an async equivalent) should be wired in.
"""
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.models.schemas import ExperimentRequest, ExperimentResponse

router = APIRouter()


@router.post(
    "/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_200_OK,
    summary="Run an observability experiment",
)
def run_experiment(body: ExperimentRequest) -> ExperimentResponse:
    """
    Accepts a prompt configuration, runs each prompt for the requested number of
    iterations, validates outputs, applies normalization and recovery logic, and
    returns a full trace log with per-run results and a summary.

    **Runs per prompt** are capped at `MAX_RUNS_PER_PROMPT` (default: 20).
    """
    # ── cap runs ──────────────────────────────────────────────────────────────
    for p in body.prompts:
        if p.runs > settings.max_runs_per_prompt:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'runs' value {p.runs} exceeds server limit of {settings.max_runs_per_prompt}",
            )

    # ── TODO: wire instrument layer ───────────────────────────────────────────
    # Convert body to the dict format expected by instrument.run_experiment:
    #
    #   import sys, pathlib
    #   sys.path.insert(0, str(pathlib.Path(__file__).parents[3] / "src"))
    #   import instrument
    #
    #   prompts_dict = body.model_dump()
    #   trace_log, _ = instrument.run_experiment(prompts=prompts_dict)
    #   return ExperimentResponse(**trace_log)
    #
    # Replace this stub once the shared instrument module is packaged or the
    # async equivalent is implemented here.

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Experiment execution is not yet implemented. See routes/experiments.py TODO.",
    )
