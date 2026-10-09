from definition.validation.validate_agent import validate_agent
from scenarios.letter_agent_document import build_letter_agent_document


def _documented():
    doc = build_letter_agent_document()
    for tool in doc["tools"]:
        tool["credentialId"] = "test-credential-id"
    return doc


def test_letter_agent_document_valid():
    report = validate_agent(_documented())
    assert report["errors"] == 0, report


def test_letter_skill_waits_for_a_human_decision():
    doc = _documented()
    skill = doc["skills"][0]
    assert skill["id"] == "compose_letter"
    assert skill["initial"] == "queued"
    states = {state["id"]: state for state in skill["states"]}

    start = states["queued"]["transitions"]
    assert [item["event"] for item in start] == ["ui.request.parse_requested"]
    assert start[0]["actions"] == ["compose_draft"]
    assert start[0]["to"] == "waiting_for_human"

    decisions = states["waiting_for_human"]["transitions"]
    assert [item["guard"] for item in decisions] == [
        "payload.decision == 'approve'",
        "payload.decision == 'correct'",
        "payload.decision == 'defer'",
    ]
    assert [item["actions"] for item in decisions] == [
        ["record_letter"],
        ["note_correction"],
        ["defer_letter"],
    ]
    assert decisions[0]["to"] == "recorded"
    assert states["recorded"]["final"] is True


def test_draft_keeps_skeleton_out_of_the_model_schema():
    doc = _documented()
    actions = {action["id"]: action for action in doc["actions"]}
    recipe = actions["compose_draft"]["recipe"]
    assert [step["command"] for step in recipe] == ["get_snapshot", "run_structured", "send_message"]

    schema = recipe[1]["input"]["schema"]
    assert schema["required"] == ["text"]
    assert set(schema["properties"]) == {"text"}

    proposal = recipe[2]["input"]["ui_proposal"]
    assert proposal["kind"] == "letter_draft"
    assert proposal["rules_applied"] == []
    assert proposal["skeleton"]["planned_days"] == "{{vars.planned_days}}"
    assert proposal["text"] == "{{steps.write.result.structured.text}}"

    recorded = actions["record_letter"]["recipe"][0]["input"]["workspace_update"]
    assert recorded["entity"] == "letter"
    assert recorded["patch"]["status"] == "recorded"
    assert recorded["patch"]["text"] == "{{vars.letter_text}}"
    assert recorded["patch"]["planned_days"] == "{{vars.planned_days}}"
