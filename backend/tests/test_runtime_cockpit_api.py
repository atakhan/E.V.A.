from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import new_ephemeral_agent_slug


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


SKILL_ID = "cockpit_skill"
START_EVENT = "request.started"


def _minimal_agent_body(*, transition_to: str = "done") -> dict:
    return {
        "skills": [
            {
                "id": SKILL_ID,
                "name": "Cockpit skill",
                "version": "1.0.0",
                "initial": "new",
                "params": [],
                "states": [
                    {
                        "id": "new",
                        "onEnter": [],
                        "final": False,
                        "transitions": [
                            {"id": "t1", "event": START_EVENT, "to": transition_to},
                        ],
                    },
                    {"id": "done", "onEnter": [], "final": True, "transitions": []},
                    {"id": "waiting", "onEnter": [], "final": False, "transitions": []},
                ],
            }
        ],
        "actions": [],
        "tools": [],
    }


def _seed_and_publish(client: TestClient, slug: str, *, transition_to: str = "done") -> None:
    draft = client.get(f"/api/agents/{slug}").json()
    updated = client.put(
        f"/api/agents/{slug}",
        json={**draft, **_minimal_agent_body(transition_to=transition_to)},
    )
    assert updated.status_code == 200, updated.text
    publish = client.post(f"/api/agents/{slug}/publish")
    assert publish.status_code == 200, publish.text


def _start_run(client: TestClient, slug: str, conversation_id: str) -> str:
    response = client.post(
        "/api/runtime/runs",
        json={
            "agentSlug": slug,
            "skillId": SKILL_ID,
            "event": {
                "type": START_EVENT,
                "payload": {"conversation_id": conversation_id},
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["skillRunId"]


@pytest.mark.integration
def test_list_runs_filtered_by_agent(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Cockpit", "slug": slug, "description": "test"})
    try:
        _seed_and_publish(client, slug)
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        run_id = _start_run(client, slug, conversation_id)

        listed = client.get("/api/runtime/runs", params={"agentSlug": slug})
        assert listed.status_code == 200, listed.text
        body = listed.json()
        assert body["total"] >= 1
        ids = {item["skillRunId"] for item in body["items"]}
        assert run_id in ids
        assert all(item["agentSlug"] == slug for item in body["items"])

        completed = client.get(
            "/api/runtime/runs",
            params={"agentSlug": slug, "status": "completed"},
        )
        assert completed.status_code == 200
        assert any(item["skillRunId"] == run_id for item in completed.json()["items"])
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_runtime_summary(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Cockpit", "slug": slug, "description": "test"})
    try:
        _seed_and_publish(client, slug)
        _start_run(client, slug, f"conv-{uuid.uuid4().hex[:8]}")

        summary = client.get("/api/runtime/summary")
        assert summary.status_code == 200, summary.text
        payload = summary.json()
        assert "totals" in payload
        assert any(agent["agentSlug"] == slug for agent in payload["agents"])

        agent_summary = client.get(f"/api/runtime/agents/{slug}/summary")
        assert agent_summary.status_code == 200, agent_summary.text
        assert agent_summary.json()["isPublished"] is True
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_cancel_run_via_api(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Cockpit", "slug": slug, "description": "test"})
    try:
        body = _minimal_agent_body(transition_to="waiting")
        draft = client.get(f"/api/agents/{slug}").json()
        updated = client.put(f"/api/agents/{slug}", json={**draft, **body})
        assert updated.status_code == 200, updated.text
        publish = client.post(f"/api/agents/{slug}/publish")
        assert publish.status_code == 200, publish.text

        run_id = _start_run(client, slug, f"conv-{uuid.uuid4().hex[:8]}")
        waiting = client.get(f"/api/runtime/runs/{run_id}")
        assert waiting.json()["status"] == "waiting"

        cancelled = client.post(f"/api/runtime/runs/{run_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"

        listed = client.get(
            "/api/runtime/runs",
            params={"agentSlug": slug, "status": "cancelled"},
        )
        assert any(item["skillRunId"] == run_id for item in listed.json()["items"])
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_cancel_run_without_agent_slug_in_vars(client: TestClient, db_session):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Cockpit", "slug": slug, "description": "test"})
    try:
        _seed_and_publish(client, slug, transition_to="waiting")
        run_id = _start_run(client, slug, f"conv-{uuid.uuid4().hex[:8]}")

        from infrastructure.models.tables import SkillRunRow

        row = db_session.get(SkillRunRow, run_id)
        assert row is not None
        vars_data = dict(row.vars or {})
        vars_data.pop("_agent_slug", None)
        row.vars = vars_data
        db_session.commit()

        cancelled = client.post(f"/api/runtime/runs/{run_id}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["status"] == "cancelled"
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_find_run_by_conversation_endpoint(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Cockpit", "slug": slug, "description": "test"})
    try:
        body = _minimal_agent_body(transition_to="waiting")
        draft = client.get(f"/api/agents/{slug}").json()
        updated = client.put(f"/api/agents/{slug}", json={**draft, **body})
        assert updated.status_code == 200, updated.text
        publish = client.post(f"/api/agents/{slug}/publish")
        assert publish.status_code == 200, publish.text

        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        run_id = _start_run(client, slug, conversation_id)

        found = client.get(
            "/api/runtime/runs/by-conversation",
            params={"conversationId": conversation_id},
        )
        assert found.status_code == 200, found.text
        payload = found.json()
        assert payload["skillRunId"] == run_id
        assert payload["items"][0]["skillRunId"] == run_id
        assert payload["items"][0]["skillId"]
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_get_run_includes_extended_fields(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Cockpit", "slug": slug, "description": "test"})
    try:
        _seed_and_publish(client, slug)
        run_id = _start_run(client, slug, f"conv-{uuid.uuid4().hex[:8]}")

        detail = client.get(f"/api/runtime/runs/{run_id}")
        assert detail.status_code == 200, detail.text
        payload = detail.json()
        assert payload["agentSlug"] == slug
        assert payload["skillId"] == SKILL_ID
        assert payload["publicationVersion"]
        assert payload["createdAt"]
        assert payload["updatedAt"]
    finally:
        client.delete(f"/api/agents/{slug}")
