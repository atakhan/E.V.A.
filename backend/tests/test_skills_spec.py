from definition.mappers.skill_mapper import skill_from_document
from runtime.fsm_engine import action_completed_event_type
from runtime.guards import evaluate_guard, is_valid_guard_syntax


def test_skill_from_document_loads_params():
    skill = skill_from_document(
        {
            "id": "process_foreman_request",
            "version": "1.0.0",
            "initial": "NEW",
            "params": [
                {"name": "request_id", "type": "string", "required": True},
            ],
            "states": [{"id": "NEW", "onEnter": [], "final": True, "transitions": []}],
        }
    )
    assert skill.version == "1.0.0"
    assert len(skill.params) == 1
    assert skill.params[0].name == "request_id"
    assert skill.params[0].type == "string"
    assert skill.params[0].required is True


def test_action_completed_event_type():
    assert action_completed_event_type("parse_request") == "action.parse_request.completed"


def test_guard_result_namespace_and_comparisons():
    scope_vars = {"needs_clarification": True}
    payload = {"result": {"needs_clarification": True, "missing_fields": ["qty"]}}

    assert evaluate_guard(
        "result.needs_clarification == true",
        vars=scope_vars,
        payload=payload,
    )
    assert evaluate_guard(
        "result.missing_fields.length == 1",
        vars=scope_vars,
        payload=payload,
    )
    assert evaluate_guard(
        "result.missing_fields.length > 0",
        vars=scope_vars,
        payload=payload,
    )
    assert is_valid_guard_syntax("result.confidence >= 0.90")
