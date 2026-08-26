import os

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(scope="session", autouse=True)
def _test_env():
    os.environ.setdefault("EVA_TELEGRAM_MODE", "stub")
    os.environ.setdefault("EVA_CREDENTIALS_KEY", Fernet.generate_key().decode())
    os.environ.setdefault("EVA_DEFAULT_SKILL_IDS", "foreman=process_foreman_request")
    yield
