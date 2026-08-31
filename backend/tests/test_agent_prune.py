from unittest.mock import MagicMock

from definition.services.agent_service import AgentService, prune_ephemeral_agents


def test_is_ephemeral_slug():
    service = AgentService(MagicMock())

    assert service.is_ephemeral_slug("eva-test-abc123") is True
    assert service.is_ephemeral_slug("test-agent-deadbeef") is True
    assert service.is_ephemeral_slug("web-agent-deadbeef") is True
    assert service.is_ephemeral_slug("cred-agent-deadbeef") is True
    assert service.is_ephemeral_slug("foreman") is False
    assert service.is_ephemeral_slug("supplier") is False
    assert service.is_ephemeral_slug("my-procurement-bot") is False


def test_prune_ephemeral_agents_removes_only_test_slugs(monkeypatch):
    session = MagicMock()
    service = MagicMock()
    service.list_agents.return_value = [
        {"slug": "foreman"},
        {"slug": "eva-test-111"},
        {"slug": "my-agent"},
        {"slug": "test-agent-222"},
    ]
    service.is_ephemeral_slug.side_effect = lambda slug: slug in {"eva-test-111", "test-agent-222"}

    monkeypatch.setattr("definition.services.agent_service.AgentService", lambda _session: service)

    removed = prune_ephemeral_agents(session)

    assert removed == ["eva-test-111", "test-agent-222"]
    service.delete_agent.assert_any_call("eva-test-111")
    service.delete_agent.assert_any_call("test-agent-222")
    session.flush.assert_called_once()
