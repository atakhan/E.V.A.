import pytest
from fastapi.testclient import TestClient

from app.main import app
from infrastructure.db.session import session_scope
from tests.scenario_fixtures import publish_supplier_agent
from tools.web_client import WebClientHttp
from unittest.mock import patch


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_supplier_agent_seeded_with_web_client(client: TestClient):
    with session_scope() as session:
        publish_supplier_agent(session)
        session.commit()

    agents = client.get("/api/agents")
    assert agents.status_code == 200
    slugs = [item["slug"] for item in agents.json()]
    assert "supplier" in slugs

    credentials = client.get("/api/agents/supplier/credentials", params={"toolId": "web_client"})
    assert credentials.status_code == 200
    assert len(credentials.json()) >= 1

    mock_health = {"ok": True, "_status_code": 200, "_duration_ms": 5}
    credential_id = credentials.json()[0]["id"]
    with patch.object(WebClientHttp, "health", return_value=mock_health):
        verify = client.post(f"/api/agents/supplier/credentials/{credential_id}/verify")
    assert verify.status_code == 200
    assert verify.json()["meta"].get("verified") is True


@pytest.mark.integration
def test_supplier_ingress_accepts_dev_inbound_key(client: TestClient):
    with session_scope() as session:
        publish_supplier_agent(session)
        session.commit()

    response = client.post(
        "/api/channels/web/supplier/events",
        headers={"Authorization": "Bearer dev-inbound-key"},
        json={
            "sessionId": "ai-supplier:main",
            "type": "channel.message.received",
            "payload": {"text": "integration hello", "conversation_id": "ai-supplier:main"},
        },
    )
    assert response.status_code == 200
    assert response.json()["queued"] is True
