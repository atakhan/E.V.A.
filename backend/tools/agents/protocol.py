from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from definition.agent_protocol import NO_REPLY, NOT_PUBLISHED, judge
from definition.interaction_manifest import allow_inbound, allow_outbound, normalize_interaction_manifest
from domain.events import ToolResult

NO_PEER = "нет связи с агентом"
NOT_FOUND = "агент не найден"
SELF = "нельзя писать себе"


class AgentDirectory(Protocol):
    def agent_exists(self, agent_slug: str) -> bool: ...

    def interaction_manifest(self, agent_slug: str) -> dict[str, Any]: ...

    def published_skills(self, agent_slug: str) -> list[dict[str, Any]] | None: ...

    def deliver(
        self,
        agent_slug: str,
        skill_id: str,
        payload: dict[str, Any],
        *,
        source: str = "agents",
    ) -> None: ...


@dataclass(frozen=True)
class DeliveryPlan:
    agent_slug: str
    skill_id: str
    reply_allowed: bool


def prepare_agent_delivery(
    directory: AgentDirectory,
    *,
    sender_agent: str,
    target_agent_slug: str,
    matter: str,
    waits: bool,
    reply: bool,
    reply_allowed: bool,
) -> DeliveryPlan | str:
    """Return who receives the message, or a decline reason."""
    target = target_agent_slug.strip()
    sender = sender_agent.strip()
    if not target:
        return NOT_FOUND
    if target == sender:
        return SELF
    if reply and not reply_allowed:
        return NO_REPLY
    if not directory.agent_exists(target):
        return NOT_FOUND
    sender_manifest = normalize_interaction_manifest(directory.interaction_manifest(sender))
    if not allow_outbound(sender_manifest, target):
        return NO_PEER
    target_manifest = normalize_interaction_manifest(directory.interaction_manifest(target))
    if not allow_inbound(target_manifest, sender):
        return NO_PEER
    skills = directory.published_skills(target)
    if skills is None:
        return NOT_PUBLISHED
    decision = judge(skills, matter, waits)
    if not decision.deliver or not decision.skill_id:
        return decision.reason or NOT_FOUND
    return DeliveryPlan(
        agent_slug=target,
        skill_id=decision.skill_id,
        reply_allowed=decision.reply_allowed,
    )


def decline_result(reason: str) -> ToolResult:
    return ToolResult(ok=True, data={"delivered": False, "reason": reason})
