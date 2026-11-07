from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from tests.conftest import authenticate_client


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_register_login_me_logout(client: TestClient):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"

    register = client.post("/api/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201, register.text
    assert register.json()["email"] == email

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204

    denied = client.get("/api/auth/me")
    assert denied.status_code == 401

    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.integration
def test_constructor_requires_auth(client: TestClient):
    response = client.get("/api/projects")
    assert response.status_code == 401


@pytest.mark.integration
def test_project_isolation_between_users(client: TestClient):
    settings = get_settings()
    authenticate_client(client)

    slug = f"p-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/projects",
        json={"name": "Owned", "slug": slug, "description": ""},
    )
    assert created.status_code == 201, created.text

    other = TestClient(app)
    email = f"other-{uuid.uuid4().hex[:8]}@example.com"
    registered = other.post(
        "/api/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert registered.status_code == 201, registered.text

    listed = other.get("/api/projects")
    assert listed.status_code == 200
    assert all(item["slug"] != slug for item in listed.json())

    missing = other.get(f"/api/projects/{slug}")
    assert missing.status_code == 404

    # Bootstrap admin still sees the project.
    admin_list = client.get("/api/projects")
    assert admin_list.status_code == 200
    assert any(item["slug"] == slug for item in admin_list.json())

    # Cleanup under admin session.
    client.delete(f"/api/projects/{slug}")
    assert settings.bootstrap_admin_email


@pytest.mark.integration
def test_agent_isolation_between_users(client: TestClient):
    authenticate_client(client)
    slug = f"eva-test-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/agents",
        json={"name": "Owned agent", "slug": slug, "description": ""},
    )
    assert created.status_code == 201, created.text

    other = TestClient(app)
    email = f"agent-user-{uuid.uuid4().hex[:8]}@example.com"
    assert (
        other.post("/api/auth/register", json={"email": email, "password": "password123"}).status_code
        == 201
    )

    assert other.get(f"/api/agents/{slug}").status_code == 404
    assert client.get(f"/api/agents/{slug}").status_code == 200
    client.delete(f"/api/agents/{slug}")


@pytest.mark.integration
def test_web_channel_works_without_user_session(client: TestClient):
    """Machine inbound key auth must not depend on constructor login cookie."""
    authenticate_client(client)
    slug = f"eva-test-{uuid.uuid4().hex[:8]}"
    assert (
        client.post(
            "/api/agents",
            json={"name": "Channel agent", "slug": slug, "description": ""},
        ).status_code
        == 201
    )
    created = client.post(
        f"/api/agents/{slug}/credentials",
        json={
            "toolId": "web_client",
            "name": "ingress",
            "secret": {
                "backend_base_url": "http://localhost:8765",
                "outbound_api_key": "out-key",
                "inbound_api_key": "inbound-secret-key",
            },
        },
    )
    assert created.status_code == 201, created.text

    anonymous = TestClient(app)
    response = anonymous.post(
        f"/api/channels/web/{slug}/events",
        headers={"Authorization": "Bearer inbound-secret-key"},
        json={
            "sessionId": "s1",
            "type": "web.state.changed",
            "payload": {"ok": True},
        },
    )
    assert response.status_code in {200, 202}, response.text
    client.delete(f"/api/agents/{slug}")
