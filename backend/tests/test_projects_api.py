from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_project_membership_roundtrip(client: TestClient):
    slug = f"proj-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/projects",
        json={"name": "Стройка", "slug": slug, "description": "Письма и снабжение"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    runtime_slug = body.get("runtimeAgentSlug") or ""
    try:
        assert body["slug"] == slug
        assert body["agents"] == []
        runtime = client.get(f"/api/agents/{runtime_slug}")
        assert runtime.status_code == 200, runtime.text
        runtime_body = runtime.json()
        assert runtime_body["kind"] == "runtime"
        assert runtime_body["name"] == "Стройка"
        assert [skill["systemRole"] for skill in runtime_body["skills"]] == [
            "talk_to_agent",
            "talk_to_human",
            "life",
        ]
        renamed = client.patch(f"/api/projects/{slug}", json={"name": "Офис"})
        assert renamed.status_code == 200, renamed.text
        runtime_after = client.get(f"/api/agents/{runtime_slug}")
        assert runtime_after.status_code == 200
        assert runtime_after.json()["name"] == "Офис"
        updated = client.patch(
            f"/api/projects/{slug}",
            json={"agents": [{"agentSlug": "sous-letter", "x": 40, "y": 80}]},
        )
        assert updated.status_code == 200, updated.text
        membership = updated.json()["agents"]
        assert membership[0]["x"] == 40.0
        assert membership[0]["y"] == 80.0
        if client.get("/api/agents/sous-letter").status_code == 404:
            assert membership == [{"agentSlug": "sous-letter", "x": 40.0, "y": 80.0}]
        else:
            assert membership[0]["agentSlug"] != "sous-letter"
            assert membership[0]["originSlug"] == "sous-letter"

        listed = client.get("/api/projects")
        assert listed.status_code == 200
        assert any(item["slug"] == slug for item in listed.json())
    finally:
        deleted = client.delete(f"/api/projects/{slug}")
        assert deleted.status_code == 204
        assert client.get(f"/api/agents/{runtime_slug}").status_code == 404


@pytest.mark.integration
def test_project_agent_is_a_fork_of_the_library(client: TestClient):
    origin = f"lib-{uuid.uuid4().hex[:8]}"
    project_a = f"proj-{uuid.uuid4().hex[:8]}"
    project_b = f"proj-{uuid.uuid4().hex[:8]}"
    created_agent = client.post(
        "/api/agents",
        json={"name": "Корневой", "slug": origin, "description": "стартовая конфигурация"},
    )
    assert created_agent.status_code == 201, created_agent.text
    forks: list[str] = []
    try:
        for project_slug in (project_a, project_b):
            created = client.post(
                "/api/projects",
                json={"name": project_slug, "slug": project_slug, "description": ""},
            )
            assert created.status_code == 201, created.text
            added = client.patch(
                f"/api/projects/{project_slug}",
                json={"agents": [{"agentSlug": origin, "x": 0, "y": 0}]},
            )
            assert added.status_code == 200, added.text
            member = added.json()["agents"][0]
            assert member["originSlug"] == origin
            assert member["agentSlug"] != origin
            forks.append(member["agentSlug"])

        assert forks[0] != forks[1]
        renamed = client.put(
            f"/api/agents/{forks[0]}",
            json={"name": "Форк проекта", "description": "своя ветка"},
        )
        assert renamed.status_code == 200, renamed.text
        library = client.get(f"/api/agents/{origin}")
        other = client.get(f"/api/agents/{forks[1]}")
        assert library.json()["name"] == "Корневой"
        assert other.json()["name"] == "Корневой"
        assert renamed.json()["kind"] == "fork"
        assert renamed.json()["originSlug"] == origin
    finally:
        for project_slug in (project_a, project_b):
            client.delete(f"/api/projects/{project_slug}")
        client.delete(f"/api/agents/{origin}")
        for fork_slug in forks:
            assert client.get(f"/api/agents/{fork_slug}").status_code == 404
