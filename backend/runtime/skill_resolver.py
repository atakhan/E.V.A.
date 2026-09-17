from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from runtime.publication_loader import load_published_agent_body
from runtime.skill_routing import find_skills_for_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillResolution:
    skill_id: str | None = None
    reason: str = ""
    error: str | None = None
    ambiguous: list[str] = field(default_factory=list)
    deprecated: bool = False

    @property
    def ok(self) -> bool:
        return self.skill_id is not None and self.error is None


def env_default_skill_id(agent_slug: str) -> str | None:
    """Deprecated server-wide fallback from EVA_DEFAULT_SKILL_IDS."""
    mapping: dict[str, str] = {}
    for part in get_settings().default_skill_ids.split(","):
        part = part.strip()
        if "=" in part:
            slug, skill_id = part.split("=", 1)
            mapping[slug.strip()] = skill_id.strip()
    return mapping.get(agent_slug)


def resolve_skill_for_event(
    agent_body: dict[str, Any],
    event_type: str,
    *,
    explicit_skill_id: str | None = None,
    agent_slug: str = "",
    allow_env_fallback: bool = True,
) -> SkillResolution:
    """Resolve which skill should handle a new inbound event.

    Priority:
    1. explicit skillId from the client
    2. unique match by initial-state transition for event_type
    3. defaultSkillId when it disambiguates multiple event matches
    4. defaultSkillId on the agent document
    5. deprecated EVA_DEFAULT_SKILL_IDS env mapping (logged)
    """
    skills = [skill for skill in agent_body.get("skills", []) if isinstance(skill, dict)]
    skill_ids = {str(skill["id"]) for skill in skills if skill.get("id")}

    if explicit_skill_id:
        if explicit_skill_id not in skill_ids:
            return SkillResolution(
                error=f"Unknown skillId '{explicit_skill_id}' for agent '{agent_slug or agent_body.get('slug', '')}'",
            )
        return SkillResolution(skill_id=explicit_skill_id, reason="explicit")

    discovered = find_skills_for_event(agent_body, event_type)
    default_skill_id = str(agent_body.get("defaultSkillId") or "").strip() or None

    if len(discovered) == 1:
        return SkillResolution(skill_id=discovered[0], reason="event_route")

    if len(discovered) > 1:
        if default_skill_id and default_skill_id in discovered:
            return SkillResolution(skill_id=default_skill_id, reason="default_among_matches")
        return SkillResolution(
            error=(
                f"Ambiguous routing for event '{event_type}': skills {discovered}. "
                "Pass skillId in the request or set defaultSkillId on the agent."
            ),
            ambiguous=list(discovered),
        )

    if default_skill_id:
        if default_skill_id not in skill_ids:
            return SkillResolution(
                error=f"defaultSkillId '{default_skill_id}' does not exist on agent document",
            )
        return SkillResolution(skill_id=default_skill_id, reason="agent_default")

    if allow_env_fallback and agent_slug:
        env_skill_id = env_default_skill_id(agent_slug)
        if env_skill_id:
            if env_skill_id not in skill_ids:
                return SkillResolution(
                    error=(
                        f"EVA_DEFAULT_SKILL_IDS maps '{agent_slug}' to unknown skill '{env_skill_id}'"
                    ),
                )
            logger.warning(
                "Routing agent '%s' event '%s' via deprecated EVA_DEFAULT_SKILL_IDS — "
                "set defaultSkillId on the agent document instead",
                agent_slug,
                event_type,
            )
            return SkillResolution(
                skill_id=env_skill_id,
                reason="env_fallback",
                deprecated=True,
            )

    slug = agent_slug or str(agent_body.get("slug") or "")
    return SkillResolution(
        error=(
            f"No skill handles event '{event_type}' for agent '{slug}'. "
            "Add an initial transition, set defaultSkillId on the agent, or pass skillId."
        ),
    )


def resolve_skill_for_agent_slug(
    session: Session,
    *,
    agent_slug: str,
    event_type: str,
    explicit_skill_id: str | None = None,
    allow_env_fallback: bool = True,
) -> SkillResolution:
    body = load_published_agent_body(session, agent_slug)
    if body is None:
        return SkillResolution(error=f"No publication for agent '{agent_slug}'")
    return resolve_skill_for_event(
        body,
        event_type,
        explicit_skill_id=explicit_skill_id,
        agent_slug=agent_slug,
        allow_env_fallback=allow_env_fallback,
    )

