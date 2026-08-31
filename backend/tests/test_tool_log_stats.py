from definition.services.tool_api_log_service import ToolApiLogService
from runtime.tool_executor import _build_log_preview
from domain.events import ToolResult


def test_build_log_preview_from_text():
    preview = _build_log_preview(
        tool_id="web_client",
        command="send_message",
        args={"text": "hello world"},
        result=ToolResult(ok=True, data={"sent": {}}),
    )
    assert preview == "hello world"


def test_stats_empty_agent():
    service = ToolApiLogService(session=None)  # type: ignore[arg-type]
    # smoke: method exists and structure is documented
    assert hasattr(service, "stats")
