import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from definition.validation.validate_agent import validate_agent
from scenarios.foreman_agent_document import build_foreman_agent_document


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_validate_foreman_document_has_no_errors():
    doc = build_foreman_agent_document()
    for tool in doc.get("tools", []):
        if tool.get("toolId") == "telegram":
            tool["credentialId"] = "00000000-0000-0000-0000-000000000001"
    report = validate_agent(doc)
    assert report["errors"] == 0


def test_validate_unknown_action():
    doc = build_foreman_agent_document()
    doc["skills"][0]["states"][0]["transitions"][0]["actions"] = ["missing_action"]
    report = validate_agent(doc)
    assert report["errors"] >= 1
    assert any(issue["code"] == "unknown_action" for issue in report["issues"])


@pytest.mark.integration
def test_agents_crud_and_publish(client: TestClient, ephemeral_agent_slug: str):
    slug = ephemeral_agent_slug

    get_resp = client.get(f"/api/agents/{slug}")
    assert get_resp.json()["slug"] == slug

    validate_resp = client.post(f"/api/agents/{slug}/validate")
    assert validate_resp.status_code == 200

    publish_resp = client.post(f"/api/agents/{slug}/publish")
    assert publish_resp.status_code in (200, 400)


@pytest.mark.integration
def test_tools_catalog(client: TestClient):
    resp = client.get("/api/tools/catalog")
    assert resp.status_code == 200
    tools = resp.json()
    assert any(tool["id"] == "telegram" for tool in tools)


@pytest.mark.integration
def test_runtime_foreman_happy_path(client: TestClient, foreman_agent: str):
    conversation_id = f"tg:chat:test-{uuid.uuid4().hex[:8]}"
    first = client.post(
        "/api/runtime/runs",
        json={
            "agentSlug": foreman_agent,
            "skillId": "process_foreman_request",
            "event": {
                "type": "channel.message.received",
                "payload": {
                    "conversation_id": conversation_id,
                    "text": "Нужны грибки на объект срочно",
                },
            },
        },
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["currentState"] == "WAITING_FOR_FOREMAN"
    assert first_body["status"] == "waiting"
    run_id = first_body["skillRunId"]

    second = client.post(
        "/api/runtime/events",
        json={
            "type": "channel.message.received",
            "skillRunId": run_id,
            "payload": {
                "conversation_id": conversation_id,
                "text": "Грибки — это крепёж М8",
            },
        },
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["currentState"] == "READY"
    assert second_body["status"] == "completed"


@pytest.mark.integration
def test_telegram_webhook_queues_event(client: TestClient, foreman_agent: str):
    resp = client.post(
        f"/api/channels/telegram/{foreman_agent}",
        json={
            "update_id": 1,
            "message": {
                "message_id": 42,
                "chat": {"id": 1001},
                "text": "hello",
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["queued"] is True
