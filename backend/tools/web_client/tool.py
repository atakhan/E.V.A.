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
        http: WebClientHttp | None,
        agent_id: str,
        agent_slug: str,
        credential_id: str | None,
        session,
        binding_config: dict[str, Any] | None = None,
        docker_rewrite: bool = False,
        docker_host: str = "host.docker.internal",
    ) -> None:
        self.http = http
        self.agent_id = agent_id
        self.agent_slug = agent_slug
        self.credential_id = credential_id
        self.session = session
        self.binding_config = binding_config or {}
        self.docker_rewrite = docker_rewrite
        self.docker_host = docker_host

    def _http_for(self, context: dict[str, Any]) -> WebClientHttp | None:
        vars_ = context.get("vars") or {}
        credential_id = str(vars_.get("web_client_credential_id") or "").strip()
        if credential_id and self.session is not None:
            from tools.credential_resolver import get_credential_secret

            try:
                secret = get_credential_secret(self.session, self.agent_id, credential_id)
            except KeyError:
                secret = {}
            base_url = str(secret.get("backend_base_url") or "")
            if base_url:
                return WebClientHttp(
                    base_url=base_url,
                    outbound_api_key=str(secret.get("outbound_api_key") or ""),
                    config=self.binding_config,
                    docker_rewrite=self.docker_rewrite,
                    docker_host=self.docker_host,
                )
        return self.http

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
        http = self._http_for(context)
        if http is None:
            return ToolResult(ok=False, error="web_client application is not configured")

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
            response = http.send_message(session_id=session_id, text=text, meta=meta)
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
        http = self._http_for(context)
        if http is None:
            return ToolResult(ok=False, error="web_client application is not configured")

        local = WebClientSessionStore().get_snapshot(agent_slug=self.agent_slug, session_id=session_id)
        try:
            remote = http.get_snapshot(session_id=session_id)
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
