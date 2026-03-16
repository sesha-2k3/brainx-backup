"""
Test: Health and readiness endpoints via HTTP.

Behaviors:
  - "GET /health returns 200 with ok status"
  - "GET /ready returns 200 when DB is connected"
"""

import pytest


@pytest.mark.asyncio
class TestHealthEndpoints:

    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_ready_returns_connected(self, client):
        resp = await client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["database"] == "connected"
