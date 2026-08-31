from unittest.mock import MagicMock, patch

from domain.events import Event
from tools.telegram import TelegramTool


@patch("tools.telegram.tool.httpx.post")
def test_telegram_tool_send_message(mock_post: MagicMock):
    mock_post.return_value = MagicMock(
        is_success=True,
        json=lambda: {
            "ok": True,
            "result": {"message_id": 99, "chat": {"id": 12345}},
        },
        text="ok",
    )

    tool = TelegramTool("123:TOKEN")
    result = tool.cmd_send_message(
        {"chat_id": "tg:chat:12345", "text": "hello"},
        {"vars": {}, "skill_run_id": "run-1"},
    )

    assert result.ok is True
    assert result.data["sent"]["text"] == "hello"
    assert len(result.events) == 1
    assert result.events[0].type == "channel.message.sent"


def test_normalize_telegram_update():
    from app.api.channels.telegram_utils import normalize_telegram_update

    payload = normalize_telegram_update(
        {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "chat": {"id": 777},
                "text": "Привет",
            },
        }
    )
    assert payload is not None
    assert payload["conversation_id"] == "tg:chat:777"
    assert payload["text"] == "Привет"
    assert payload["telegram_message_id"] == 10
