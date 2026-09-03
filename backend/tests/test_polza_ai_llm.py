from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tools.polza import PolzaAiLlmTool, PolzaApiError, PolzaClient


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_polza_client_balance_parses_amount():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"amount":"12.5"}'
    mock_response.json.return_value = {"amount": "12.5"}

    with patch("tools.polza.client.httpx.request", return_value=mock_response) as request:
        client = PolzaClient("test-key")
        body = client.get_balance()
        assert body["amount"] == "12.5"
        assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_polza_client_raises_on_error():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.content = b'{"error":{"message":"bad key"}}'
    mock_response.text = '{"error":{"message":"bad key"}}'
    mock_response.json.return_value = {"error": {"message": "bad key"}}

    with patch("tools.polza.client.httpx.request", return_value=mock_response):
        client = PolzaClient("bad")
        with pytest.raises(PolzaApiError) as exc:
            client.get_balance()
        assert "bad key" in str(exc.value)


def test_polza_ai_llm_run_returns_text():
    mock_response = {
        "model": "openai/gpt-4o-mini",
        "choices": [{"message": {"content": "hello"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch.object(PolzaClient, "chat_completion", return_value=mock_response):
        tool = PolzaAiLlmTool(
            api_key="k",
            default_model="openai/gpt-4o-mini",
            base_url="https://polza.ai/api/v1",
            agent_id="agent-1",
            credential_id="cred-1",
            session=MagicMock(),
        )
        result = tool.cmd_run({"prompt": "hi"}, {"vars": {}})
        assert result.ok is True
        assert result.data["text"] == "hello"


@pytest.mark.integration
def test_polza_models_endpoint_public(client: TestClient, foreman_agent: str):
    slug = foreman_agent
    mock_models = {
        "data": [
            {
                "id": "openai/gpt-4o-mini",
                "name": "GPT-4o Mini",
                "type": "chat",
                "top_provider": {"context_length": 128000},
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"{}"
    mock_response.json.return_value = mock_models

    with patch("tools.polza.client.httpx.request", return_value=mock_response):
        resp = client.get(f"/api/agents/{slug}/tools/polza_ai_llm/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["id"] == "openai/gpt-4o-mini"
