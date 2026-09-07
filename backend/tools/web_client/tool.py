from __future__ import annotations

from typing import Any

from domain.events import ToolResult
from tools.base import BaseTool
from tools.web_client.http import WebClientHttp, WebClientHttpError


class WebClientTool(BaseTool):
    id = "web_client"
    commands = ("send_message", "get_snapshot")

    def __init__(
        self,
        *,
        http: WebClientHttp,
        agent_id: str,
        agent_slug: str,
        credential_id: str | None,
        session,
    ) -> None:
        self.http = http
        self.agent_id = agent_id
        self.agent_slug = agent_slug
        self.credential_id = credential_id
        self.session = session

    def cmd_send_message(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        from infrastructure.stores.web_client_store import WebClientSessionStore

        vars_ = context.get("vars", {})
        session_id = str(
            args.get("session_id")
            or args.get("sessionId")
            or vars_.get("conversation_id")
            or ""
        )
        text = str(args.get("text") or "")
        if not session_id:
            return ToolResult(ok=False, error="session_id is required for web_client.send_message")
        if not text:
            return ToolResult(ok=False, error="text is required for web_client.send_message")

        meta = args.get("meta") if isinstance(args.get("meta"), dict) else {}
        if isinstance(args.get("workspace_update"), dict):
            meta = {**meta, "workspace_update": args["workspace_update"]}
        if args.get("ui_proposal") is not None:
            meta = {**meta, "ui_proposal": args["ui_proposal"]}
        from runtime.presence import presence_for_conversation

        presence = presence_for_conversation(self.session, session_id)
        if presence:
            meta = {**meta, "presence": presence}
        try:
            response = self.http.send_message(session_id=session_id, text=text, meta=meta)
        except WebClientHttpError as exc:
            return ToolResult(ok=False, error=str(exc))

        outbox_message = {
            "sessionId": session_id,
            "text": text,
            "meta": meta,
            "response": {k: v for k, v in response.items() if not k.startswith("_")},
        }
        WebClientSessionStore().push_outbox(
            agent_slug=self.agent_slug,
            session_id=session_id,
            message=outbox_message,
        )
        return ToolResult(ok=True, data={"sent": outbox_message, "statusCode": response.get("_status_code")})

    def cmd_get_snapshot(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        from infrastructure.stores.web_client_store import WebClientSessionStore

        vars_ = context.get("vars", {})
        session_id = str(
            args.get("session_id")
            or args.get("sessionId")
            or vars_.get("conversation_id")
            or ""
        )
        if not session_id:
            return ToolResult(ok=False, error="session_id is required for web_client.get_snapshot")

        local = WebClientSessionStore().get_snapshot(agent_slug=self.agent_slug, session_id=session_id)
        try:
            remote = self.http.get_snapshot(session_id=session_id)
        except WebClientHttpError as exc:
            if local is not None:
                return ToolResult(ok=True, data={"snapshot": local, "source": "eva_cache"})
            return ToolResult(ok=False, error=str(exc))

        snapshot = {**(local or {}), **{k: v for k, v in remote.items() if not k.startswith("_")}}
        WebClientSessionStore().upsert_snapshot(
            agent_slug=self.agent_slug,
            session_id=session_id,
            payload=snapshot,
        )
        return ToolResult(ok=True, data={"snapshot": snapshot, "source": "remote"})
