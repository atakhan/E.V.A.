from __future__ import annotations

from domain.action import ActionDefinition, ActionRecipeStep
from domain.agent import AgentDefinition
from domain.events import Event
from domain.skill import FsmState, FsmTransition, SkillDefinition, SkillParam
from domain.tool import ToolCommandDef, ToolDefinition
from runtime.event_router import EventRouter, RuntimeCatalog
from tools.registry import ToolRegistry
from tools.telegram import TelegramStubTool


def build_foreman_definitions() -> tuple[
    AgentDefinition,
    SkillDefinition,
    dict[str, ActionDefinition],
    list[ToolDefinition],
]:
    skill = SkillDefinition(
        id="process_foreman_request",
        name="Process foreman request",
        version="1.0.0",
        initial="NEW",
        params=[
            SkillParam(name="request_id", type="string", required=False),
            SkillParam(name="conversation_id", type="string", required=False),
        ],
        states=[
            FsmState(
                id="NEW",
                transitions=[
                    FsmTransition(
                        id="t_new_msg",
                        event="channel.message.received",
                        actions=["parse_request"],
                        to="ANALYZING",
                    )
                ],
            ),
            FsmState(
                id="ANALYZING",
                transitions=[
                    FsmTransition(
                        id="t_needs_clarify",
                        event="action.parse_request.completed",
                        guard="result.needs_clarification == true",
                        to="CLARIFYING",
                    ),
                    FsmTransition(
                        id="t_ready_direct",
                        event="action.parse_request.completed",
                        guard="result.needs_clarification == false",
                        to="READY",
                    ),
                ],
            ),
            FsmState(
                id="CLARIFYING",
                on_enter=["clarify"],
                transitions=[
                    FsmTransition(
                        id="t_wait",
                        event="action.clarify.completed",
                        to="WAITING_FOR_FOREMAN",
                    )
                ],
            ),
            FsmState(
                id="WAITING_FOR_FOREMAN",
                transitions=[
                    FsmTransition(
                        id="t_foreman_reply",
                        event="channel.message.received",
                        guard="payload.conversation_id == vars.conversation_id",
                        to="READY",
                    )
                ],
            ),
            FsmState(id="READY", final=True),
        ],
    )

    actions = {
        "parse_request": ActionDefinition(
            id="parse_request",
            name="Parse foreman request",
            version="0.1.0",
            policy="auto",
            recipe=[
                ActionRecipeStep(
                    id="llm_parse",
                    tool="llm",
                    command="parse_request",
                    input={"text": "{{vars.last_message}}"},
                )
            ],
        ),
        "clarify": ActionDefinition(
            id="clarify",
            name="Clarify with foreman",
            version="0.1.0",
            policy="auto",
            recipe=[
                ActionRecipeStep(
                    id="tg_ask",
                    tool="telegram",
                    command="send_message",
                    input={
                        "chat_id": "{{vars.conversation_id}}",
                        "text": "Уточните, пожалуйста: что именно нужно по грибкам?",
                    },
                )
            ],
        ),
    }

    tools = [
        ToolDefinition(
            id="llm",
            name="LLM",
            commands=[
                ToolCommandDef(id="parse_request"),
                ToolCommandDef(id="run"),
                ToolCommandDef(id="run_structured"),
            ],
        ),
        ToolDefinition(
            id="telegram",
            name="Telegram",
            commands=[ToolCommandDef(id="send_message")],
            events=["channel.message.sent"],
        ),
    ]

    agent = AgentDefinition(
        id="procurement",
        name="Procurement Agent",
        version="0.1.0",
        skill_ids=[skill.id],
        action_ids=list(actions.keys()),
        tool_ids=[t.id for t in tools],
    )
    return agent, skill, actions, tools


def build_foreman_router(registry: ToolRegistry | None = None) -> EventRouter:
    _, skill, actions, _ = build_foreman_definitions()
    reg = registry or ToolRegistry.with_stubs()
    return EventRouter(
        catalog=RuntimeCatalog(skill=skill, actions=actions),
        registry=reg,
    )


def scripted_events() -> list[Event]:
    conversation_id = "tg:chat:foreman-42"
    return [
        Event(
            type="channel.message.received",
            payload={
                "conversation_id": conversation_id,
                "text": "Нужны грибки на объект срочно",
            },
        ),
        Event(
            type="channel.message.received",
            payload={
                "conversation_id": conversation_id,
                "text": "Грибки — это крепёж М8, 200 штук",
            },
        ),
    ]


def run_foreman_happy_path(
    router: EventRouter | None = None,
) -> tuple[EventRouter, list]:
    """Drive the two-event happy path; returns router and per-event RouterResults."""
    r = router or build_foreman_router()
    results = [r.route(ev) for ev in scripted_events()]
    return r, results


def get_telegram_stub(router: EventRouter) -> TelegramStubTool:
    tool = router.registry.get("telegram")
    assert isinstance(tool, TelegramStubTool)
    return tool
