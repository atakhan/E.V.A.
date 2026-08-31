from unittest.mock import MagicMock

from domain.events import ToolResult
from runtime.tool_executor import ToolExecutor
from runtime.tool_log_context import ToolLogContext, sanitize_for_log
from tools.base import BaseTool
from tools.registry import ToolRegistry


class EchoTool(BaseTool):
    id = "echo"
    commands = ("ping",)

    def cmd_ping(self, args, context):
        return ToolResult(ok=True, data={"text": args.get("text", "")})


def test_sanitize_for_log_redacts_secrets():
    payload = {
        "api_key": "secret",
        "text": "hello",
        "nested": {"bot_token": "x", "value": 1},
    }
    sanitized = sanitize_for_log(payload)
    assert sanitized["api_key"] == "***"
    assert sanitized["text"] == "hello"
    assert sanitized["nested"]["bot_token"] == "***"
    assert sanitized["nested"]["value"] == 1


def test_tool_executor_appends_log():
    session = MagicMock()
    registry = ToolRegistry([EchoTool()])
    log_ctx = ToolLogContext(session=session, agent_id="agent-1", agent_slug="test")
    executor = ToolExecutor(registry, log_context=log_ctx)

    result = executor.execute(
        "echo",
        "ping",
        {"text": "hi", "api_key": "hidden"},
        {"skill_run_id": "run-1", "action_id": "reply", "vars": {}},
    )

    assert result.ok is True
    session.add.assert_called_once()
    row = session.add.call_args.args[0]
    assert row.tool_id == "echo"
    assert row.command == "ping"
    assert row.status == "ok"
    assert row.skill_run_id == "run-1"
    assert row.action_id == "reply"
    assert row.request_summary["input"]["api_key"] == "***"
