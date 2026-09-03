from definition.validation.validate_agent import validate_agent
from scenarios.conversation_skill import build_razgovor_skill
from scenarios.supplier_assistant_agent_document import build_supplier_assistant_agent_document


def test_supplier_assistant_agent_document_valid():
    doc = build_supplier_assistant_agent_document()
    for tool in doc["tools"]:
        if tool.get("toolId") in {"web_client", "polza_ai_llm"}:
            tool["credentialId"] = "test-credential-id"
    report = validate_agent(doc)
    assert report["errors"] == 0, report
    assert doc["defaultSkillId"] == "razgovor"
    action_ids = {action["id"] for action in doc["actions"]}
    assert {"draft_reply", "send_reply"} <= action_ids
    tool_types = {tool["toolId"] for tool in doc["tools"]}
    assert {"web_client", "polza_ai_llm"} <= tool_types


def test_razgovor_skill_fsm_variant_b():
    skill = build_razgovor_skill("2026-01-01T00:00:00+00:00")
    assert skill["id"] == "razgovor"
    assert skill["name"] == "Разговор"
    assert skill["initial"] == "IDLE"

    states = {state["id"]: state for state in skill["states"]}
    assert set(states) == {"IDLE", "THINKING", "REPLIED"}

    idle_transition = states["IDLE"]["transitions"][0]
    assert idle_transition["event"] == "channel.message.received"
    assert idle_transition["actions"] == ["draft_reply"]
    assert idle_transition["to"] == "THINKING"

    thinking_transition = states["THINKING"]["transitions"][0]
    assert thinking_transition["event"] == "action.draft_reply.completed"
    assert thinking_transition["actions"] == ["send_reply"]
    assert thinking_transition["to"] == "REPLIED"

    replied_transition = states["REPLIED"]["transitions"][0]
    assert replied_transition["event"] == "action.send_reply.completed"
    assert replied_transition["actions"] == []
    assert replied_transition["to"] == "IDLE"
