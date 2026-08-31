import os
import uuid

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text

from app.config import get_settings


def _services_available() -> bool:
    if os.getenv("EVA_SKIP_INTEGRATION") == "1":
        return False
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()

        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def new_ephemeral_agent_slug() -> str:
    return f"eva-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session", autouse=True)
def _test_env():
    os.environ.setdefault("EVA_TELEGRAM_MODE", "stub")
    os.environ.setdefault("EVA_CREDENTIALS_KEY", Fernet.generate_key().decode())
    os.environ.setdefault("EVA_DEFAULT_SKILL_IDS", "foreman=process_foreman_request")
    yield


@pytest.fixture
def db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


@pytest.fixture
def ephemeral_agent_slug(client):
    """Create a throwaway agent for integration tests and delete it afterwards."""
    slug = new_ephemeral_agent_slug()
    response = client.post(
        "/api/agents",
        json={"name": "Test", "slug": slug, "description": "integration test"},
    )
    assert response.status_code == 201, response.text
    yield slug
    client.delete(f"/api/agents/{slug}")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: tests that require postgres and redis",
    )


def pytest_collection_modifyitems(config, items):
    if _services_available():
        return

    skip = pytest.mark.skip(
        reason=(
            "postgres/redis unavailable — run "
            "`docker compose run --rm backend pytest` "
            "or start deps with `docker compose up -d postgres redis`"
        )
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
