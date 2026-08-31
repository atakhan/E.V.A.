import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.integration
def test_credentials_crud_and_secret_not_exposed(client: TestClient, ephemeral_agent_slug: str):
    slug = ephemeral_agent_slug

    create = client.post(
        f"/api/agents/{slug}/credentials",
        json={
            "toolId": "telegram",
            "name": "Test bot",
            "secret": {"bot_token": "123:ABC"},
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["toolId"] == "telegram"
    assert "bot_token" not in str(body)

    listed = client.get(f"/api/agents/{slug}/credentials")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "bot_token" not in str(listed.json())

    credential_id = body["id"]
    deleted = client.delete(f"/api/agents/{slug}/credentials/{credential_id}")
    assert deleted.status_code == 204

    listed_after = client.get(f"/api/agents/{slug}/credentials")
    assert listed_after.json() == []
