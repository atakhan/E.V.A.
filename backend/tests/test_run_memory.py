from datetime import datetime, timezone
from types import SimpleNamespace

from runtime.skill_run_query import run_detail_from_row, visible_run_memory


def test_visible_memory_drops_service_keys_and_lifts_params():
    params, variables = visible_run_memory(
        {
            "_agent_slug": "sous-letter",
            "_desk": {"workspace": {}},
            "_desk_text": "{}",
            "_skill_params": {"tone": "formal", "_hidden": "no"},
            "last_message": "привет",
            "count": 0,
            "ok": False,
            "note": "",
        }
    )

    assert params == {"tone": "formal"}
    assert variables == {"last_message": "привет", "count": 0, "ok": False, "note": ""}


def test_visible_memory_treats_missing_params_as_empty():
    params, variables = visible_run_memory({"_skill_params": "not-a-dict", "text": "a"})
    assert params == {}
    assert variables == {"text": "a"}

    params, variables = visible_run_memory(None)
    assert params == {}
    assert variables == {}


def test_run_detail_returns_readable_memory_only():
    moment = datetime(2026, 10, 12, tzinfo=timezone.utc)
    detail = run_detail_from_row(
        SimpleNamespace(
            id="run-1",
            agent_slug="sous-letter",
            skill_id="compose_letter",
            status="waiting",
            current_state="wait_review",
            publication_version="0.1.1",
            conversation_id="c1",
            error=None,
            history=["start", "wait_review"],
            vars={
                "_agent_slug": "sous-letter",
                "_desk": {"secret": True},
                "_skill_params": {"tone": "formal"},
                "last_message": "привет",
            },
            created_at=moment,
            updated_at=moment,
        )
    )

    assert detail["params"] == {"tone": "formal"}
    assert detail["vars"] == {"last_message": "привет"}
    assert "_desk" not in detail["vars"]
    assert detail["currentState"] == "wait_review"
