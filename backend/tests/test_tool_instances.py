from __future__ import annotations

from runtime.tool_instance_resolver import resolve_recipe_tool


def test_resolve_instance_id_direct():
    agent = {
        "tools": [
            {"id": "foreman_tg", "toolId": "telegram", "enabled": True, "credentialId": "c1"},
        ]
    }
    resolved = resolve_recipe_tool(agent, "foreman_tg")
    assert resolved is not None
    assert resolved.status == "ok"
    assert resolved.instance_id == "foreman_tg"
    assert resolved.type_id == "telegram"


def test_resolve_type_fallback_single_instance():
    agent = {
        "tools": [
            {"id": "telegram", "toolId": "telegram", "enabled": True},
        ]
    }
    resolved = resolve_recipe_tool(agent, "telegram")
    assert resolved is not None
    assert resolved.status == "ok"
    assert resolved.instance_id == "telegram"


def test_resolve_type_ambiguous():
    agent = {
        "tools": [
            {"id": "tg1", "toolId": "telegram", "enabled": True},
            {"id": "tg2", "toolId": "telegram", "enabled": True},
        ]
    }
    resolved = resolve_recipe_tool(agent, "telegram")
    assert resolved is not None
    assert resolved.status == "ambiguous"


def test_find_instance_by_credential():
    from runtime.tool_instance_resolver import find_instance_by_credential

    agent = {
        "tools": [
            {"id": "tg1", "toolId": "telegram", "enabled": True, "credentialId": "cred-a"},
            {"id": "tg2", "toolId": "telegram", "enabled": True, "credentialId": "cred-b"},
        ]
    }
    assert find_instance_by_credential(agent, "cred-b") == "tg2"
