from __future__ import annotations

import json
from typing import Any

from domain.events import ToolResult
from tools.base import BaseTool
from tools.polza.client import PolzaApiError, PolzaClient


def _truncate(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _messages_from_args(args: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(args.get("messages"), list) and args["messages"]:
        return list(args["messages"])

    system = args.get("system") or args.get("system_prompt")
    prompt = args.get("prompt") or args.get("text") or context.get("vars", {}).get("last_message", "")
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": str(system)})
    messages.append({"role": "user", "content": str(prompt)})
    return messages


def _extract_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else str(content or "")


class PolzaAiLlmTool(BaseTool):
    id = "polza_ai_llm"
    commands = ("run", "run_structured", "parse_request")

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str,
        base_url: str,
        agent_id: str,
        credential_id: str | None,
        session,
    ) -> None:
        self.client = PolzaClient(api_key, base_url=base_url)
        self.default_model = default_model
        self.agent_id = agent_id
        self.credential_id = credential_id
        self.session = session

    def cmd_run(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        return self._complete(command="run", args=args, context=context)

    def cmd_run_structured(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        schema = args.get("schema")
        response_format: dict[str, Any]
        if isinstance(schema, dict) and schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": str(args.get("schema_name") or "result"),
                    "schema": schema,
                    "strict": True,
                },
            }
        else:
            response_format = {"type": "json_object"}
        return self._complete(
            command="run_structured",
            args=args,
            context=context,
            response_format=response_format,
        )

    def cmd_parse_request(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text = str(args.get("text") or context.get("vars", {}).get("last_message", ""))
        schema = {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "needs_clarification": {"type": "boolean"},
                "raw_text": {"type": "string"},
            },
            "required": ["item", "needs_clarification", "raw_text"],
            "additionalProperties": False,
        }
        result = self._complete(
            command="parse_request",
            args={
                **args,
                "system": (
                    "Ты парсер заявок снабжения. Верни JSON: item, needs_clarification, raw_text. "
                    "needs_clarification=true если позиция неоднозначна (например «грибки»)."
                ),
                "prompt": text,
            },
            context=context,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "parse_request", "schema": schema, "strict": True},
            },
        )
        if not result.ok:
            return result

        parsed_payload = result.data.get("structured") if isinstance(result.data, dict) else None
        if not isinstance(parsed_payload, dict):
            try:
                parsed_payload = json.loads(str(result.data.get("text", "{}")))
            except (TypeError, json.JSONDecodeError, AttributeError):
                parsed_payload = {
                    "item": "материал",
                    "needs_clarification": False,
                    "raw_text": text,
                }

        needs = bool(parsed_payload.get("needs_clarification"))
        return ToolResult(
            ok=True,
            data={
                "parsed": parsed_payload,
                "needs_clarification": needs,
                "usage": result.data.get("usage") if isinstance(result.data, dict) else {},
                "model": result.data.get("model") if isinstance(result.data, dict) else None,
            },
        )

    def _complete(
        self,
        *,
        command: str,
        args: dict[str, Any],
        context: dict[str, Any],
        response_format: dict[str, Any] | None = None,
    ) -> ToolResult:
        model = str(args.get("model") or self.default_model)
        messages = _messages_from_args(args, context)

        try:
            response = self.client.chat_completion(
                model=model,
                messages=messages,
                response_format=response_format,
                max_tokens=args.get("max_tokens"),
                temperature=args.get("temperature"),
            )
        except PolzaApiError as exc:
            return ToolResult(ok=False, error=str(exc))

        text = _extract_text(response)
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        structured: dict[str, Any] | None = None
        if response_format is not None and text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    structured = parsed
            except json.JSONDecodeError:
                structured = None

        data: dict[str, Any] = {
            "text": text,
            "model": response.get("model", model),
            "usage": usage,
            "promptPreview": _truncate(
                next(
                    (
                        str(msg.get("content", ""))
                        for msg in reversed(messages)
                        if msg.get("role") == "user"
                    ),
                    "",
                )
            ),
        }
        if structured is not None:
            data["structured"] = structured
            data["ok"] = True
        return ToolResult(ok=True, data=data)
