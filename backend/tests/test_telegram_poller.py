from unittest.mock import MagicMock, patch

from infrastructure.models.tables import ToolCredentialRow
from workers.telegram_poller import _is_pollable_credential, _poll_credential


def test_skip_dev_stub_credential():
    cred = ToolCredentialRow(
        id="1",
        agent_id="a",
        tool_id="telegram",
        name="stub",
        secret_encrypted="plain:{}",
        meta={"dev_stub": True},
    )
    assert _is_pollable_credential(cred, "123:REAL") is False


def test_skip_test_dev_token():
    cred = ToolCredentialRow(
        id="1",
        agent_id="a",
        tool_id="telegram",
        name="stub",
        secret_encrypted="plain:{}",
        meta={},
    )
    assert _is_pollable_credential(cred, "000000:TEST-DEV-TOKEN") is False


@patch("workers.telegram_poller.publish_event")
@patch("workers.telegram_poller.httpx.get")
def test_poll_handles_401(mock_get: MagicMock, _publish: MagicMock):
    mock_get.return_value = MagicMock(status_code=401, is_success=False, text="Unauthorized")
    cred = ToolCredentialRow(
        id="c1",
        agent_id="a",
        tool_id="telegram",
        name="bot",
        secret_encrypted="plain:{}",
        meta={},
    )
    assert _poll_credential(cred, "foreman", "123:INVALID") == 0
