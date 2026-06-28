"""
Test bootstrap for the microservice.

Sets minimal environment variables so app.core.config loads without
raising errors, then exposes a FastAPI TestClient fixture.
"""
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "test-sk-not-real")
os.environ.setdefault("LOGS_ROOT_DIR", "/tmp/svc-test-logs")

from app.main import app  # noqa: E402 — import after env setup


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
