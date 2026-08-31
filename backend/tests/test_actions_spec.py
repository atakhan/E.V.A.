from definition.mappers.action_mapper import normalize_action_document, normalize_recipe_step
from runtime.expression_resolver import build_action_input, resolve_value


def test_normalize_recipe_step_migrates_legacy_args():
    step = normalize_recipe_step(
        {
            "id": "s1",
            "tool": "llm",
            "command": "run",
            "args": '{"text": "{{vars.last_message}}"}',
        },
        fallback_id="step_1",
    )
    assert step.input == {"text": "{{vars.last_message}}"}
    assert step.when == ""


def test_normalize_action_document_spec_fields():
    action = normalize_action_document(
        {
            "id": "parse_request",
            "version": "1.0.0",
            "policy": "needs_human",
            "inputSchema": {"type": "object"},
            "outputSchema": {"type": "object"},
            "recipe": [
                {
                    "id": "llm_parse",
                    "tool": "llm",
                    "command": "parse_request",
                    "input": {"text": "{{input.message}}"},
                    "when": "vars.needs_clarification == true",
                }
            ],
        }
    )
    assert action.id == "parse_request"
    assert action.version == "1.0.0"
    assert action.policy == "needs_human"
    assert action.input_schema == {"type": "object"}
    assert action.recipe[0].input == {"text": "{{input.message}}"}
    assert action.recipe[0].when == "vars.needs_clarification == true"


def test_resolve_value_templates_and_legacy_vars():
    scope = {
        "input": {"message": "hello"},
        "vars": {"conversation_id": "tg:1"},
        "steps": {"crm": {"result": {"count": 0}}},
    }
    resolved = resolve_value(
        {
            "text": "{{input.message}}",
            "chat_id": "{{vars.conversation_id}}",
            "legacy": "${vars.conversation_id}",
            "count": "{{steps.crm.result.count}}",
        },
        scope,
    )
    assert resolved == {
        "text": "hello",
        "chat_id": "tg:1",
        "legacy": "tg:1",
        "count": "0",
    }


def test_build_action_input_from_vars():
    action_input = build_action_input(
        {
            "request_id": "r1",
            "last_message": "нужны грибки",
            "conversation_id": "tg:chat:1",
            "_internal": "skip",
        }
    )
    assert action_input["request_id"] == "r1"
    assert action_input["message"] == "нужны грибки"
    assert action_input["conversation_id"] == "tg:chat:1"
    assert "_internal" not in action_input
