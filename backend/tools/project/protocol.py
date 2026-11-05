from __future__ import annotations

from typing import Any, Protocol

from dataclasses import dataclass

from definition.agent_protocol import (
    NO_CONNECTOR,
    NO_PROJECT,
    NO_REPLY,
    NOT_HERE,
    NOT_PUBLISHED,
    judge,
)
from domain.events import ToolResult


class AgentDirectory(Protocol):
    def project_of(self, agent_slug: str) -> str | None: ...

    def runtime_agent(self, project_slug: str) -> str | None: ...

    def hosts(self, project_slug: str, agent_slug: str) -> bool: ...

    def published_skills(self, agent_slug: str) -> list[dict[str, Any]] | None: ...

    def deliver(self, agent_slug: str, skill_id: str, payload: dict[str, Any]) -> None: ...


def target_agent(
    directory: AgentDirectory,
    *,
    project_slug: str,
    agent_slug: str,
) -> str | None:
    if agent_slug:
        if not directory.hosts(project_slug, agent_slug):
            return None
        return agent_slug
    return directory.runtime_agent(project_slug)


def connector_allows(own_project: str, connectors: list[str], target_project: str) -> bool:
    if target_project == own_project:
        return True
    return target_project in {item.strip() for item in connectors if item.strip()}


@dataclass(frozen=True)
class DeliveryPlan:
    agent_slug: str
    project_slug: str
    skill_id: str
    reply_allowed: bool


def prepare_delivery(
    directory: AgentDirectory,
    *,
    sender_agent: str,
    connectors: list[str],
    target_project: str,
    target_agent_slug: str,
    matter: str,
    waits: bool,
    reply: bool,
    reply_allowed: bool,
) -> DeliveryPlan | str:
    """Return who receives the message, or a decline reason."""
    own = directory.project_of(sender_agent)
    if not own:
        return NO_PROJECT
    project_slug = target_project.strip() or own
    if not connector_allows(own, connectors, project_slug):
        return NO_CONNECTOR
    if reply and not reply_allowed:
        return NO_REPLY
    agent_slug = target_agent(directory, project_slug=project_slug, agent_slug=target_agent_slug.strip())
    if not agent_slug:
        return NOT_HERE
    skills = directory.published_skills(agent_slug)
    if skills is None:
        return NOT_PUBLISHED
    decision = judge(skills, matter, waits)
    if not decision.deliver or not decision.skill_id:
        return decision.reason or NOT_HERE
    return DeliveryPlan(
        agent_slug=agent_slug,
        project_slug=project_slug,
        skill_id=decision.skill_id,
        reply_allowed=decision.reply_allowed,
    )


def decline_result(reason: str) -> ToolResult:
    return ToolResult(ok=True, data={"delivered": False, "reason": reason})
