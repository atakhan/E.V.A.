from __future__ import annotations

import logging
import time
from typing import Any

from app.config import get_settings
from definition.catalog.builtin_tools import get_command_input_schema
from definition.catalog.field_schema import apply_defaults
from definition.validation.validate_tool_command_input import validate_command_input_errors_only
from domain.action_run import ToolExecution, ToolExecutionStatus
from domain.events import ToolResult
from infrastructure.stores.postgres_tool_execution_store import PostgresToolExecutionStore
from runtime.tool_log_context import ToolLogContext, sanitize_for_log
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_TRANSIENT_MARKERS = ("timeout", "503", "502", "504", "connection", "temporarily")


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        log_context: ToolLogContext | None = None,
        tool_execution_store: PostgresToolExecutionStore | None = None,
    ) -> None:
        self.registry = registry
        self._log_context = log_context
        self._tool_execution_store = tool_execution_store

    def execute(
        self,
        tool_id: str,
        command: str,
        args: dict[str, Any],
        context: dict[str, Any],
        *,
        max_attempts: int = 1,
    ) -> ToolResult:
        execution = ToolExecution(
            action_run_id=str(context.get("action_run_id") or ""),
            tool_instance_id=tool_id,
            command=command,
            input=args,
            status=ToolExecutionStatus.running,
        )
        if self._tool_execution_store is not None and execution.action_run_id:
            self._tool_execution_store.create(execution)

        last_result: ToolResult | None = None
        for attempt in range(1, max(1, max_attempts) + 1):
            execution.attempt = attempt
            started = time.perf_counter()
            try:
                tool = self.registry.require(tool_id)
                prepared_args = dict(args)
                tool_type = str(getattr(tool, "tool_type", "") or tool.id)
                schema = get_command_input_schema(tool_type, command)
                if schema:
                    prepared_args = apply_defaults(schema, prepared_args)
                    validation_errors = validate_command_input_errors_only(
                        tool_type, command, prepared_args
                    )
                    mode = get_settings().tool_input_validation
                    if validation_errors:
                        message = validation_errors[0]
                        if mode == "strict":
                            result = ToolResult(ok=False, error=message)
                        elif mode == "off":
                            result = tool.handle(command, prepared_args, context)
                        elif mode == "warn":
                            logger.warning(
                                "tool input validation warning for %s.%s: %s",
                                tool_type,
                                command,
                                message,
                            )
                            result = tool.handle(command, prepared_args, context)
                        else:
                            raise RuntimeError(
                                f"invalid EVA_TOOL_INPUT_VALIDATION: {mode!r}"
                            )
                    else:
                        result = tool.handle(command, prepared_args, context)
                else:
                    result = tool.handle(command, prepared_args, context)
            except Exception as exc:  # noqa: BLE001
                result = ToolResult(ok=False, error=str(exc))
            duration_ms = int((time.perf_counter() - started) * 1000)
            last_result = result

            execution.duration_ms = duration_ms
            execution.output = dict(result.data)
            execution.error = result.error
            execution.status = ToolExecutionStatus.completed if result.ok else ToolExecutionStatus.failed
            if self._tool_execution_store is not None and execution.action_run_id:
                self._tool_execution_store.update(execution)

            if result.ok:
                self._append_log(
                    tool_id=tool_id,
                    command=command,
                    args=args,
                    context=context,
                    result=result,
                    tool=self.registry.require(tool_id),
                    duration_ms=duration_ms,
                    tool_execution_id=execution.id,
                )
                result.tool_execution_id = execution.id
                return result

            if attempt < max_attempts and _is_transient(result.error):
                time.sleep(min(0.25 * attempt, 2.0))
                continue
            break

        assert last_result is not None
        self._append_log(
            tool_id=tool_id,
            command=command,
            args=args,
            context=context,
            result=last_result,
            tool=self.registry.require(tool_id),
            duration_ms=execution.duration_ms or 0,
            tool_execution_id=execution.id,
        )
        last_result.tool_execution_id = execution.id
        return last_result

    def _append_log(
        self,
        *,
        tool_id: str,
        command: str,
        args: dict[str, Any],
        context: dict[str, Any],
        result: ToolResult,
        tool: Any,
        duration_ms: int,
        tool_execution_id: str | None = None,
    ) -> None:
        from definition.services.tool_api_log_service import ToolApiLogService

        log_ctx = self._log_context
        if log_ctx is None:
            return

        vars_ = context.get("vars") if isinstance(context.get("vars"), dict) else {}
        model = args.get("model")
        if not model and isinstance(result.data, dict):
            model = result.data.get("model")

        usage: dict[str, Any] = {}
        if isinstance(result.data, dict) and isinstance(result.data.get("usage"), dict):
            usage = result.data["usage"]

        preview = _build_log_preview(tool_id=tool_id, command=command, args=args, result=result)
        tool_type = getattr(tool, "tool_type", None) or tool_id

        request_summary = sanitize_for_log(
            {
                "preview": preview,
                "input": args,
                "actionId": context.get("action_id"),
                "skillRunId": context.get("skill_run_id"),
                "toolInstanceId": tool_id,
                "toolTypeId": tool_type,
                "actionRunId": context.get("action_run_id"),
                "toolExecutionId": tool_execution_id,
            }
        )
        response_summary = sanitize_for_log(
            {
                "data": result.data,
                "events": [
                    {"type": event.type, "payload": event.payload}
                    for event in result.events[:10]
                ],
            }
        )

        try:
            ToolApiLogService(log_ctx.session).append(
                agent_id=log_ctx.agent_id,
                tool_id=tool_type,
                command=command,
                credential_id=log_ctx.credential_for_tool(tool_id, tool),
                model=str(model) if model else None,
                status="ok" if result.ok else "error",
                request_summary=request_summary,
                response_summary=response_summary,
                usage=usage,
                duration_ms=duration_ms,
                error_message=result.error,
                skill_run_id=str(context.get("skill_run_id") or vars_.get("_skill_run_id") or "") or None,
                action_id=str(context.get("action_id") or "") or None,
                tool_execution_id=tool_execution_id,
            )
        except Exception:
            logger.exception(
                "Failed to append tool log for %s.%s (skill_run=%s)",
                tool_id,
                command,
                context.get("skill_run_id"),
            )


def _is_transient(error: str | None) -> bool:
    if not error:
        return False
    lowered = error.lower()
    return any(marker in lowered for marker in _TRANSIENT_MARKERS)


def _build_log_preview(
    *,
    tool_id: str,
    command: str,
    args: dict[str, Any],
    result: ToolResult,
) -> str | None:
    if isinstance(result.data, dict):
        for key in ("promptPreview", "text"):
            value = result.data.get(key)
            if isinstance(value, str) and value.strip():
                text = value.strip()
                return text if len(text) <= 240 else f"{text[:239]}…"

    for key in ("text", "prompt", "query"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if len(text) <= 240 else f"{text[:239]}…"

    session_id = args.get("session_id") or args.get("sessionId")
    if session_id:
        return f"{tool_id}.{command} · session {session_id}"

    return f"{tool_id}.{command}"
