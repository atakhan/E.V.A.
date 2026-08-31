from __future__ import annotations

DEFAULT_HEALTH_PATH = "/eva/health"
DEFAULT_SEND_MESSAGE_PATH = "/eva/messages"
DEFAULT_GET_SNAPSHOT_PATH = "/eva/context"
DEFAULT_AUTH_STYLE = "bearer"
DEFAULT_TIMEOUT_SEC = 30

WEB_CLIENT_DEFAULTS = {
    "healthPath": DEFAULT_HEALTH_PATH,
    "sendMessagePath": DEFAULT_SEND_MESSAGE_PATH,
    "getSnapshotPath": DEFAULT_GET_SNAPSHOT_PATH,
    "authStyle": DEFAULT_AUTH_STYLE,
    "timeoutSec": DEFAULT_TIMEOUT_SEC,
}
