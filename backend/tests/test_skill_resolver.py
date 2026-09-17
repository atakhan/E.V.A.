from scenarios.conversation_skill import build_razgovor_skill
from scenarios.foreman_agent_document import build_foreman_agent_document
from scenarios.supplier_assistant_agent_document import build_supplier_assistant_agent_document
from runtime.skill_resolver import resolve_skill_for_event


def _agent_with_chat_skills() -> dict:
    return {
        "slug": "demo",
        "defaultSkillId": "chat_b",
        "skills": [
            {
                "id": "chat_a",
                "initial": "READY",
                "states": [
                    {
                        "id": "READY",
                        "transitions": [
                            {"event": "channel.message.received", "actions": [], "to": "READY"}
                        ],
                    }
                ],
            },
            {
                "id": "chat_b",
                "initial": "READY",
                "states": [
                    {
                        "id": "READY",
                        "transitions": [
                            {"event": "channel.message.received", "actions": [], "to": "READY"}
                        ],
                    }
                ],
            },
        ],
    }


def test_resolve_explicit_skill_id():
    doc = build_supplier_assistant_agent_document()
    result = resolve_skill_for_event(
        doc,
        "channel.message.received",
        explicit_skill_id="razgovor",
        agent_slug="supplier-agent",
        allow_env_fallback=False,
    )
    assert result.ok
    assert result.skill_id == "razgovor"
    assert result.reason == "explicit"


def test_resolve_by_unique_event_route():
    doc = build_supplier_assistant_agent_document()
    result = resolve_skill_for_event(
        doc,
        "channel.message.received",
        agent_slug="supplier-agent",
        allow_env_fallback=False,
    )
    assert result.ok
    assert result.skill_id == "razgovor"
    assert result.reason == "event_route"


def test_resolve_workspace_event_routes_to_process_skill():
    doc = build_supplier_assistant_agent_document()
    result = resolve_skill_for_event(
        doc,
        "ui.request.parse_requested",
        agent_slug="supplier-agent",
        allow_env_fallback=False,
    )
    assert result.ok
    assert result.skill_id == "process_supplier_request"
    assert result.reason == "event_route"


def test_resolve_ambiguous_event_uses_default_skill_id():
    doc = _agent_with_chat_skills()
    result = resolve_skill_for_event(
        doc,
        "channel.message.received",
        agent_slug="demo",
        allow_env_fallback=False,
    )
    assert result.ok
    assert result.skill_id == "chat_b"
    assert result.reason == "default_among_matches"


def test_resolve_ambiguous_without_default_fails():
    doc = _agent_with_chat_skills()
    doc.pop("defaultSkillId")
    result = resolve_skill_for_event(
        doc,
        "channel.message.received",
        agent_slug="demo",
        allow_env_fallback=False,
    )
    assert not result.ok
    assert result.ambiguous == ["chat_a", "chat_b"]


def test_resolve_unknown_event_uses_agent_default():
    doc = build_foreman_agent_document()
    result = resolve_skill_for_event(
        doc,
        "custom.unknown.event",
        agent_slug="foreman",
        allow_env_fallback=False,
    )
    assert result.ok
    assert result.skill_id == "process_foreman_request"
    assert result.reason == "agent_default"


def test_resolve_unknown_event_without_default_fails():
    doc = build_razgovor_skill("2026-01-01T00:00:00+00:00")
    agent = {"slug": "x", "skills": [doc]}
    result = resolve_skill_for_event(
        agent,
        "custom.unknown.event",
        agent_slug="x",
        allow_env_fallback=False,
    )
    assert not result.ok
    assert "No skill handles event" in (result.error or "")


def test_resolve_env_fallback_is_deprecated(monkeypatch):
    from app.config import get_settings
    from scenarios.conversation_skill import build_razgovor_skill

    monkeypatch.setenv("EVA_DEFAULT_SKILL_IDS", "legacy=razgovor")
    get_settings.cache_clear()
    try:
        doc = build_razgovor_skill("2026-01-01T00:00:00+00:00")
        agent = {"slug": "legacy", "skills": [doc]}
        result = resolve_skill_for_event(
            agent,
            "custom.unknown.event",
            agent_slug="legacy",
            allow_env_fallback=True,
        )
        assert result.ok
        assert result.skill_id == "razgovor"
        assert result.deprecated is True
        assert result.reason == "env_fallback"
    finally:
        get_settings.cache_clear()
