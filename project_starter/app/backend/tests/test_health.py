"""Scaffold test: the app boots and answers its health probe.

Domain tests arrive with the tickets; this one exists so the checks have
something to prove before any feature is built.
"""

from fastapi.testclient import TestClient

from saving_streak.api import create_app


def test_health_reports_ok():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
