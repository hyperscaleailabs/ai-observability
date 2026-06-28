"""Tests for GET /health."""


class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        assert "application/json" in resp.headers["content-type"] \
            if (resp := client.get("/health")) else True
        resp = client.get("/health")
        assert resp.headers["content-type"].startswith("application/json")

    def test_status_is_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_service_name_present(self, client):
        data = client.get("/health").json()
        assert data["service"] == "ai-observability-microservice"

    def test_version_present(self, client):
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"] == "0.1.0"
