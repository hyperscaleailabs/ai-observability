"""
Integration tests for the Flask API (app.py).

Uses Flask's test client; the OpenAI client and instrument.run_experiment
are mocked so no network calls are made.
"""
from unittest.mock import MagicMock, patch

import pytest

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ── GET /health ───────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        resp = client.get("/health")
        assert resp.content_type == "application/json"

    def test_body_has_instrument_name(self, client):
        data = client.get("/health").get_json()
        assert data.get("instrument-name") == "ai-observability"

    def test_body_has_version(self, client):
        data = client.get("/health").get_json()
        assert "instrument-version" in data

    def test_body_has_updated(self, client):
        data = client.get("/health").get_json()
        assert "updated" in data


# ── POST /experiment — input validation ───────────────────────────────────────

class TestExperimentValidation:
    def test_no_body_returns_400(self, client):
        resp = client.post("/experiment")
        assert resp.status_code == 400

    def test_non_json_content_type_returns_400(self, client):
        resp = client.post("/experiment", data="text body", content_type="text/plain")
        assert resp.status_code == 400

    def test_missing_prompts_key_returns_400(self, client):
        resp = client.post("/experiment", json={"code": "test"})
        assert resp.status_code == 400
        assert "prompts" in resp.get_json()["error"]

    def test_prompts_not_list_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": "not a list"})
        assert resp.status_code == 400

    def test_empty_prompts_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": []})
        assert resp.status_code == 400

    def test_prompt_missing_prompt_field_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": [{"runs": 1}]})
        assert resp.status_code == 400

    def test_prompt_empty_string_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": [{"prompt": "  ", "runs": 1}]})
        assert resp.status_code == 400

    def test_runs_zero_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": [{"prompt": "p", "runs": 0}]})
        assert resp.status_code == 400

    def test_runs_not_int_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": [{"prompt": "p", "runs": "five"}]})
        assert resp.status_code == 400

    def test_runs_exceeds_limit_returns_400(self, client):
        resp = client.post("/experiment", json={"prompts": [{"prompt": "p", "runs": 9999}]})
        assert resp.status_code == 400
        assert "limit" in resp.get_json()["error"]


# ── POST /experiment — success path ───────────────────────────────────────────

class TestExperimentSuccess:
    TRACE_LOG = {
        "trace_id": "test-trace-123",
        "runs": [
            {
                "request_id": "r1",
                "trace_id": "test-trace-123",
                "prompt": "test prompt",
                "output": "{}",
                "latency": 0.5,
                "output_length": 2,
                "status": "success",
                "is_valid": True,
                "issues": [],
            }
        ],
        "summary": {
            "total_runs": 1,
            "success_count": 1,
            "valid_count": 1,
            "invalid_count": 0,
            "success_percentage": 100.0,
            "avg_latency": 0.5,
            "observed_issue_types": [],
        },
    }

    def test_valid_request_returns_200(self, client):
        with patch("app.instrument.run_experiment", return_value=(self.TRACE_LOG, MagicMock())):
            resp = client.post("/experiment", json={"prompts": [{"prompt": "test", "runs": 1}]})
        assert resp.status_code == 200

    def test_response_contains_trace_id(self, client):
        with patch("app.instrument.run_experiment", return_value=(self.TRACE_LOG, MagicMock())):
            data = client.post("/experiment", json={"prompts": [{"prompt": "test", "runs": 1}]}).get_json()
        assert data["trace_id"] == "test-trace-123"

    def test_response_contains_summary(self, client):
        with patch("app.instrument.run_experiment", return_value=(self.TRACE_LOG, MagicMock())):
            data = client.post("/experiment", json={"prompts": [{"prompt": "test", "runs": 1}]}).get_json()
        assert "summary" in data
        assert data["summary"]["total_runs"] == 1

    def test_response_contains_runs(self, client):
        with patch("app.instrument.run_experiment", return_value=(self.TRACE_LOG, MagicMock())):
            data = client.post("/experiment", json={"prompts": [{"prompt": "test", "runs": 1}]}).get_json()
        assert isinstance(data["runs"], list)

    def test_experiment_body_passed_through(self, client):
        payload = {
            "code": "my_exp",
            "prompts": [{"prompt": "do something", "runs": 2}],
        }
        with patch("app.instrument.run_experiment", return_value=(self.TRACE_LOG, MagicMock())) as mock_exp:
            client.post("/experiment", json=payload)
        called_with = mock_exp.call_args[1]["prompts"]
        assert called_with["code"] == "my_exp"


# ── POST /experiment — error path ─────────────────────────────────────────────

class TestExperimentErrors:
    def test_instrument_exception_returns_500(self, client):
        with patch("app.instrument.run_experiment", side_effect=Exception("LLM down")):
            resp = client.post("/experiment", json={"prompts": [{"prompt": "p", "runs": 1}]})
        assert resp.status_code == 500

    def test_500_response_has_error_key(self, client):
        with patch("app.instrument.run_experiment", side_effect=Exception("boom")):
            data = client.post("/experiment", json={"prompts": [{"prompt": "p", "runs": 1}]}).get_json()
        assert "error" in data

    def test_500_response_has_detail(self, client):
        with patch("app.instrument.run_experiment", side_effect=Exception("boom")):
            data = client.post("/experiment", json={"prompts": [{"prompt": "p", "runs": 1}]}).get_json()
        assert "detail" in data
