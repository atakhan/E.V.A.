from __future__ import annotations

from definition.system_skills import LIFE, system_skill
from runtime.definition_loader import build_tool_registry
from tools.pulse import PULSE_TOOL_ID, ensure_pulse_tool
from tools.pulse.inspect import connectors_snapshot, self_snapshot
from tools.pulse.tool import PulseTool


def _agent_body() -> dict:
    now = "2026-01-01T00:00:00Z"
    return {
        "slug": "demo",
        "name": "Демо",
        "kind": "library",
        "description": "тест",
        "skills": [
            system_skill("talk_to_agent", now=now),
            system_skill(LIFE, now=now),
        ],
        "tools": [
            {"id": "text-1", "toolId": "text", "enabled": True},
            {"id": "mem-1", "toolId": "memory", "enabled": True},
            {"id": "tg-1", "toolId": "telegram", "enabled": True},
        ],
        "world": {
            "addresses": [
                {"id": "agents-peer", "toolId": "agents", "name": "peer"},
                {"id": "proj-1", "toolId": "project", "config": {}},
            ]
        },
        "memory": {
            "interaction": {
                "version": 1,
                "defaultAllowInbound": False,
                "defaultAllowOutbound": False,
                "peers": [{"agentSlug": "eva", "allowInbound": True, "allowOutbound": True}],
            }
        },
    }


def test_ensure_pulse_tool_is_idempotent():
    body: dict = {"tools": []}
    ensure_pulse_tool(body)
    ensure_pulse_tool(body)
    pulse_tools = [item for item in body["tools"] if item.get("toolId") == PULSE_TOOL_ID]
    assert len(pulse_tools) == 1
    assert pulse_tools[0]["enabled"] is True


def test_self_snapshot_marks_alive_when_life_present():
    data = self_snapshot(_agent_body(), {"skill_run_id": "run-1", "vars": {"_life_run_id": "life-1"}})
    assert data["slug"] == "demo"
    assert data["alive"] is True
    assert data["life_skill"] is True
    assert data["skill_run_id"] == "run-1"
    assert data["life_run_id"] == "life-1"


def test_connectors_snapshot_statuses():
    snap = connectors_snapshot(_agent_body())
    by_tool = {item["toolId"]: item for item in snap["tools"]}
    assert by_tool["text"]["status"] == "ready"
    assert by_tool["memory"]["status"] == "unimplemented"
    assert by_tool["telegram"]["status"] == "missing_credential"
    assert snap["memory"]["status"] == "present"
    assert snap["memory"]["interaction_peers"] == 1
    assert snap["summary"]["has_life"] is True
    channels = {item["id"]: item for item in snap["channels"]}
    assert channels["agents-peer"]["status"] == "ready"
    assert channels["proj-1"]["status"] == "incomplete"
    assert any(item["status"] == "life" for item in snap["skills"])


def test_pulse_tool_registry_commands():
    body = _agent_body()
    ensure_pulse_tool(body)
    registry = build_tool_registry(body, agent_id="a1", session=None)
    tool = registry.require(PULSE_TOOL_ID)
    assert isinstance(tool, PulseTool)
    self_result = tool.handle("self", {}, {"skill_run_id": "r1", "vars": {}})
    assert self_result.ok is True
    assert self_result.data["slug"] == "demo"
    connectors = tool.handle("connectors", {}, {})
    assert connectors.ok is True
    assert "summary" in connectors.data
