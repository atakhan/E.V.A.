from __future__ import annotations

import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet | None:
    key = get_settings().credentials_key.strip()
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload).encode()
    fernet = _fernet()
    if fernet is None:
        logger.warning("EVA_CREDENTIALS_KEY not set — storing credential without encryption (dev only)")
        return "plain:" + raw.decode()
    return fernet.encrypt(raw).decode()


def decrypt_secret(token: str) -> dict[str, Any]:
    if token.startswith("plain:"):
        return json.loads(token[6:])
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError("EVA_CREDENTIALS_KEY required to decrypt credentials")
    try:
        return json.loads(fernet.decrypt(token.encode()).decode())
    except InvalidToken as exc:
        raise RuntimeError("Failed to decrypt credential") from exc
