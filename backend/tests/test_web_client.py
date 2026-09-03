import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app
from infrastructure.db.session import session_scope
from tests.scenario_fixtures import publish_minimal_web_chat_agent
from tools.web_client import WebClientHttp


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_web_client_credential_and_ingress(client: TestClient, ephemeral_agent_slug: str):
    slug = ephemeral_agent_slug
    inbound_key = "test-inbound-key"
    create = client.post(
        f"/api/agents/{slug}/credentials",
        json={
            "toolId": "web_client",
            "name": "Local backend",
            "secret": {
                "backend_base_url": "http://localhost:8765",
                "outbound_api_key": "dev-outbound-key",
                "inbound_api_key": inbound_key,
            },
        },
    )
    assert create.status_code == 201
    create_body = create.json()
    credential_id = create_body["id"]
    assert create_body.get("oneTimeSecrets", {}).get("inboundApiKey") == inbound_key

    mock_health = {"ok": True, "_status_code": 200, "_duration_ms": 12}
    with patch.object(WebClientHttp, "health", return_value=mock_health):
        verify = client.post(f"/api/agents/{slug}/credentials/{credential_id}/verify")
    assert verify.status_code == 200
    assert verify.json()["meta"].get("verified") is True

    with session_scope() as session:
        publish_minimal_web_chat_agent(session, slug, credential_id)
        session.commit()

    ingress = client.post(
        f"/api/channels/web/{slug}/events",
        headers={"Authorization": f"Bearer {inbound_key}"},
        json={
            "sessionId": "web:test:1",
            "type": "channel.message.received",
            "payload": {"text": "hello from web"},
        },
    )
    assert ingress.status_code == 200
    assert ingress.json()["queued"] is True

    integration = client.get(
        f"/api/agents/{slug}/tools/web_client/integration",
        params={"credentialId": credential_id},
    )
    assert integration.status_code == 200
    body = integration.json()
    assert body["ingressUrl"].endswith(f"/api/channels/web/{slug}/events")
    assert "localhost:8765" in body["outboundBaseUrlDocker"] or body["outboundBaseUrlDocker"]


def test_web_client_http_auth_header():
    http = WebClientHttp(
        base_url="http://example.com",
        outbound_api_key="secret",
        config={"authStyle": "x-api-key"},
    )
    headers = http._headers()
    assert headers["X-Api-Key"] == "secret"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"ok":true}'
    mock_response.json.return_value = {"ok": True}

    with patch("tools.web_client.http.httpx.request", return_value=mock_response) as request:
        http.health()
        assert request.call_args.kwargs["headers"]["X-Api-Key"] == "secret"


@pytest.mark.integration
def test_web_ingress_rejects_bad_key(client: TestClient, ephemeral_agent_slug: str):
    slug = ephemeral_agent_slug
    inbound_key = "test-inbound-key"
    create = client.post(
        f"/api/agents/{slug}/credentials",
        json={
            "toolId": "web_client",
            "name": "Local backend",
            "secret": {
                "backend_base_url": "http://localhost:8765",
                "outbound_api_key": "dev-outbound-key",
                "inbound_api_key": inbound_key,
            },
        },
    )
    assert create.status_code == 201

    resp = client.post(
        f"/api/channels/web/{slug}/events",
        headers={"Authorization": "Bearer wrong"},
        json={"sessionId": "x", "payload": {"text": "hi"}},
    )
    assert resp.status_code == 401
