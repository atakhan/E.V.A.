from __future__ import annotations

from typing import Any
from uuid import uuid4

from definition.agent_protocol import RECEIVED
from domain.events import ToolResult
from tools.agents.protocol import AgentDirectory, decline_result, prepare_agent_delivery
from tools.base import BaseTool


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


class AgentsChannelTool(BaseTool):
    """Channel to another E.V.A. agent. Peers and direction live in memory.interaction."""

    id = "agents"
    commands = ("send_message",)

    def __init__(
        self,
        *,
        agent_slug: str,
        directory: AgentDirectory | None = None,
    ) -> None:
        self.agent_slug = agent_slug
        self.directory = directory

    def cmd_send_message(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        if self.directory is None:
            return decline_result("канал агентов не собран")
        matter = str(args.get("matter") or "")
        text = str(args.get("text") or "").strip()
        if not text:
            return decline_result("пустой текст")
        conversation_id = str(args.get("conversation_id") or "").strip() or f"conv_{uuid4().hex[:12]}"
        waits = _flag(args.get("waits"))
        reply = _flag(args.get("reply"))
        vars_ = context.get("vars") if isinstance(context.get("vars"), dict) else {}
        reply_allowed = _flag(vars_.get("reply_allowed"))
        outcome = prepare_agent_delivery(
            self.directory,
            sender_agent=self.agent_slug,
            target_agent_slug=str(args.get("agent") or ""),
            matter=matter,
            waits=waits,
            reply=reply,
            reply_allowed=reply_allowed,
        )
        if isinstance(outcome, str):
            return decline_result(outcome)
        payload = {
            "conversation_id": conversation_id,
            "text": text,
            "matter": matter.strip(),
            "waits": waits,
            "reply_allowed": outcome.reply_allowed,
            "from_agent": self.agent_slug,
            "to_agent": outcome.agent_slug,
        }
        self.directory.deliver(outcome.agent_slug, outcome.skill_id, payload, source="agents")
        return ToolResult(
            ok=True,
            data={
                "delivered": True,
                "skill_id": outcome.skill_id,
                "conversation_id": conversation_id,
                "reply_allowed": outcome.reply_allowed,
                "event": RECEIVED,
            },
        )
