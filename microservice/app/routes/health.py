from fastapi import APIRouter
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health() -> HealthResponse:
    """Returns service name, version, and status. Used by load balancers and healthchecks."""
    return HealthResponse()
