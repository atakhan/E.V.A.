from domain.agent import SkillRunStatus
from scenarios.foreman_request import (
    build_foreman_router,
    get_telegram_stub,
    run_foreman_happy_path,
)


def test_foreman_happy_path_states_and_tools():
    router, results = run_foreman_happy_path()
    assert len(results) == 2

    first = results[0]
    assert first.created is True
    assert first.run.status == SkillRunStatus.waiting
    assert first.run.current_state == "WAITING_FOR_FOREMAN"
    assert first.run.history == [
        "NEW",
        "ANALYZING",
        "CLARIFYING",
        "WAITING_FOR_FOREMAN",
    ]
    assert first.run.vars.get("needs_clarification") is True

    tool_names = [(c["tool"], c["command"]) for c in first.trace.tool_calls]
    assert ("llm", "parse_request") in tool_names
    assert ("telegram", "send_message") in tool_names

    telegram = get_telegram_stub(router)
    assert len(telegram.sent) == 1
    assert telegram.sent[0]["chat_id"] == "tg:chat:foreman-42"
    assert "гриб" in telegram.sent[0]["text"].lower()

    second = results[1]
    assert second.created is False
    assert second.run.id == first.run.id
    assert second.run.status == SkillRunStatus.completed
    assert second.run.current_state == "READY"
    assert second.run.history[-1] == "READY"
    assert "READY" in second.run.history


def test_foreman_resume_requires_same_conversation():
    router = build_foreman_router()
    from domain.events import Event

    first = router.route(
        Event(
            type="channel.message.received",
            payload={
                "conversation_id": "tg:chat:A",
                "text": "Нужны грибки",
            },
        )
    )
    assert first.run.status == SkillRunStatus.waiting

    # Different conversation starts a new run instead of resuming
    other = router.route(
        Event(
            type="channel.message.received",
            payload={
                "conversation_id": "tg:chat:B",
                "text": "Нужны грибки тоже",
            },
        )
    )
    assert other.created is True
    assert other.run.id != first.run.id
