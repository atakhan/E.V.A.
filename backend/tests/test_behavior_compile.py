from __future__ import annotations

from definition.behavior.compile import compile_behavior
from definition.behavior.equivalence import fsm_behaviorally_equivalent
from definition.behavior.ids import COMPILER_VERSION
from definition.behavior.lift import lift_fsm_to_behavior
from definition.behavior.narrative import behavior_narrative
from scenarios.conversation_skill import build_razgovor_skill


def _razgovor_states():
    skill = build_razgovor_skill("2026-01-01T00:00:00+00:00")
    return skill["states"], skill["initial"]


def test_compile_is_deterministic():
    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    first = compile_behavior(graph)
    second = compile_behavior(graph)
    assert first["ok"] and second["ok"]
    a = first["artifact"]
    b = second["artifact"]
    assert a["compilerVersion"] == COMPILER_VERSION
    assert a["initial"] == b["initial"]
    assert a["states"] == b["states"]


def test_lift_razgovor_shape():
    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    types = [node["type"] for node in graph["nodes"]]
    assert types.count("wait") == 1
    assert types.count("do") == 2
    assert "end" not in types
    action_ids = {node["actionId"] for node in graph["nodes"] if node["type"] == "do"}
    assert action_ids == {"draft_reply", "send_reply"}
    wait = next(node for node in graph["nodes"] if node["type"] == "wait")
    assert wait["waitFor"]["type"] == "input"
    assert wait["waitFor"]["event"] == "channel.message.received"
    assert graph["entry"] == wait["id"]
    loops = [edge for edge in graph["edges"] if edge["kind"] == "loop"]
    assert loops


def test_lift_compile_razgovor_equivalent():
    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    result = compile_behavior(graph)
    assert result["ok"]
    artifact = result["artifact"]
    assert fsm_behaviorally_equivalent(
        states,
        initial,
        artifact["states"],
        artifact["initial"],
    )


def test_compile_twice_equivalent_to_self():
    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    artifact = compile_behavior(graph)["artifact"]
    again = compile_behavior(graph)["artifact"]
    assert fsm_behaviorally_equivalent(
        artifact["states"],
        artifact["initial"],
        again["states"],
        again["initial"],
    )


def test_origin_ids_required():
    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    artifact = compile_behavior(graph)["artifact"]
    for state in artifact["states"]:
        assert state["originNodeId"]
        for transition in state["transitions"]:
            assert transition["originNodeId"]
            assert transition["originEdgeId"]


def test_branching_compile_preserves_guards():
    graph = {
        "version": 1,
        "entry": "w1",
        "nodes": [
            {
                "id": "w1",
                "type": "wait",
                "title": "Когда приходит сообщение",
                "waitFor": {"type": "event", "event": "channel.message.received"},
            },
            {
                "id": "d1",
                "type": "decide",
                "title": "",
                "question": "Нашли несколько подходящих материалов?",
                "branches": [
                    {
                        "id": "b_yes",
                        "label": "Да",
                        "guard": "results.length > 1",
                        "to": "do_many",
                    },
                    {
                        "id": "b_no",
                        "label": "Нет",
                        "guard": "results.length == 1",
                        "to": "do_one",
                    },
                ],
            },
            {"id": "do_many", "type": "do", "title": "Показать варианты", "actionId": "show_variants"},
            {"id": "do_one", "type": "do", "title": "Предложить", "actionId": "propose"},
            {"id": "end1", "type": "end", "title": "Задача завершена"},
        ],
        "edges": [
            {"id": "e1", "from": "w1", "to": "d1", "kind": "next"},
            {"id": "e2", "from": "do_many", "to": "end1", "kind": "next"},
            {"id": "e3", "from": "do_one", "to": "end1", "kind": "next"},
        ],
    }
    result = compile_behavior(graph, action_ids={"show_variants", "propose"})
    assert result["ok"], result["errors"]
    wait_state = next(state for state in result["artifact"]["states"] if state["originNodeId"] == "w1")
    guards = {item["guard"] for item in wait_state["transitions"]}
    actions = {tuple(item["actions"]) for item in wait_state["transitions"]}
    assert "results.length > 1" in guards
    assert "results.length == 1" in guards
    assert ("show_variants",) in actions
    assert ("propose",) in actions


def test_materialize_publish_stamps_compiler_and_states():
    from definition.behavior.materialize import materialize_skill_execution

    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    skill = {"id": "razgovor", "initial": initial, "states": states, "behavior": graph}
    result = materialize_skill_execution(skill, compiled_at="2026-01-01T00:00:00+00:00")
    assert result["ok"]
    artifact = result["skill"]["execution"]
    assert artifact["compilerVersion"] == COMPILER_VERSION
    assert artifact["compiledAt"] == "2026-01-01T00:00:00+00:00"
    assert result["skill"]["states"] == artifact["states"]
    assert fsm_behaviorally_equivalent(states, initial, artifact["states"], artifact["initial"])


def test_narrative_razgovor():
    states, initial = _razgovor_states()
    graph = lift_fsm_to_behavior(states, initial)
    text = behavior_narrative(graph)
    assert "Когда" in text
    assert "Возвращаюсь" in text
