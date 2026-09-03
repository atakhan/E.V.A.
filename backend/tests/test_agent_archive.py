from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import new_ephemeral_agent_slug
from tests.test_runtime_cockpit_api import (
    SKILL_ID,
    START_EVENT,
    _minimal_agent_body,
    _seed_and_publish,
    _start_run,
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_archive_hides_from_default_list(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Archive me", "slug": slug, "description": "test"})

    try:
        archived = client.post(f"/api/agents/{slug}/archive")
        assert archived.status_code == 200, archived.text
        assert archived.json()["archivedAt"]

        active = client.get("/api/agents")
        assert all(item["slug"] != slug for item in active.json())

        with_archived = client.get("/api/agents", params={"includeArchived": True})
        match = next(item for item in with_archived.json() if item["slug"] == slug)
        assert match["archivedAt"]
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_archive_blocks_publish_and_upsert(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Archive me", "slug": slug, "description": "test"})
    draft = client.get(f"/api/agents/{slug}").json()

    try:
        assert client.post(f"/api/agents/{slug}/archive").status_code == 200

        upsert = client.put(f"/api/agents/{slug}", json={**draft, "name": "Changed"})
        assert upsert.status_code == 409, upsert.text

        publish = client.post(f"/api/agents/{slug}/publish")
        assert publish.status_code == 409, publish.text
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_archive_blocks_new_runtime_run(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Archive me", "slug": slug, "description": "test"})
    _seed_and_publish(client, slug)

    try:
        assert client.post(f"/api/agents/{slug}/archive").status_code == 200

        response = client.post(
            "/api/runtime/runs",
            json={
                "agentSlug": slug,
                "skillId": SKILL_ID,
                "event": {"type": START_EVENT, "payload": {"conversation_id": str(uuid.uuid4())}},
            },
        )
        assert response.status_code == 409, response.text
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_unarchive_restores_publish(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Archive me", "slug": slug, "description": "test"})
    _seed_and_publish(client, slug, transition_to="done")

    try:
        assert client.post(f"/api/agents/{slug}/archive").status_code == 200
        assert client.post(f"/api/agents/{slug}/unarchive").status_code == 200

        draft = client.get(f"/api/agents/{slug}").json()
        assert draft.get("archivedAt") in (None, "")

        publish = client.post(f"/api/agents/{slug}/publish")
        assert publish.status_code == 200, publish.text
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_archive_cancels_active_runs(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Archive me", "slug": slug, "description": "test"})
    _seed_and_publish(client, slug, transition_to="waiting")
    conversation_id = str(uuid.uuid4())
    run_id = _start_run(client, slug, conversation_id)

    try:
        assert client.post(f"/api/agents/{slug}/archive").status_code == 200

        run = client.get(f"/api/runtime/runs/{run_id}")
        assert run.status_code == 200, run.text
        assert run.json()["status"] == "cancelled"
    finally:
        client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_archived_agent_excluded_from_runtime_summary(client: TestClient):
    slug = new_ephemeral_agent_slug()
    client.post("/api/agents", json={"name": "Archive me", "slug": slug, "description": "test"})
    _seed_and_publish(client, slug)
    _start_run(client, slug, str(uuid.uuid4()))

    try:
        assert client.post(f"/api/agents/{slug}/archive").status_code == 200

        summary = client.get("/api/runtime/summary")
        assert summary.status_code == 200, summary.text
        slugs = [item["agentSlug"] for item in summary.json()["agents"]]
        assert slug not in slugs

        agent_summary = client.get(f"/api/runtime/agents/{slug}/summary")
        assert agent_summary.status_code == 200, agent_summary.text
        assert agent_summary.json()["archived"] is True
    finally:
        client.delete(f"/api/agents/{slug}")
