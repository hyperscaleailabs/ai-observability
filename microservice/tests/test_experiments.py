"""
Tests for POST /api/v1/experiments.

The endpoint currently returns 501 (scaffold stub). These tests verify
request validation via Pydantic and the placeholder response, and are
designed to be updated as the implementation is filled in.
"""
from unittest.mock import patch


class TestExperimentValidation:
    """Pydantic / FastAPI input validation fires before the handler."""

    def test_empty_body_returns_422(self, client):
        resp = client.post("/api/v1/experiments", json={})
        assert resp.status_code == 422

    def test_missing_prompts_field_returns_422(self, client):
        resp = client.post("/api/v1/experiments", json={"code": "test"})
        assert resp.status_code == 422

    def test_empty_prompts_list_returns_422(self, client):
        resp = client.post("/api/v1/experiments", json={"prompts": []})
        assert resp.status_code == 422

    def test_prompt_too_short_returns_422(self, client):
        resp = client.post("/api/v1/experiments", json={
            "prompts": [{"prompt": "", "runs": 1}]
        })
        assert resp.status_code == 422

    def test_runs_zero_returns_422(self, client):
        resp = client.post("/api/v1/experiments", json={
            "prompts": [{"prompt": "test", "runs": 0}]
        })
        assert resp.status_code == 422

    def test_runs_exceeds_max_returns_422(self, client):
        # Pydantic le=50 catches this before the handler's settings check
        resp = client.post("/api/v1/experiments", json={
            "prompts": [{"prompt": "test", "runs": 51}]
        })
        assert resp.status_code == 422

    def test_valid_minimal_request_reaches_handler(self, client):
        # Stub returns 501; confirms valid body passes Pydantic validation
        resp = client.post("/api/v1/experiments", json={
            "prompts": [{"prompt": "Return valid JSON.", "runs": 1}]
        })
        assert resp.status_code == 501

    def test_valid_full_request_reaches_handler(self, client):
        resp = client.post("/api/v1/experiments", json={
            "code": "ci_test",
            "description": "CI scaffold test",
            "prompts": [
                {
                    "prompt": "Return only valid JSON.",
                    "runs": 2,
                    "validators": ["validate_output_json_object"],
                    "system_message": "Be precise.",
                    "apply_json_normalization": True,
                    "scenario": "baseline",
                }
            ],
        })
        assert resp.status_code == 501

    def test_501_has_detail(self, client):
        resp = client.post("/api/v1/experiments", json={
            "prompts": [{"prompt": "p", "runs": 1}]
        })
        assert "detail" in resp.json()
