from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from scenarios.foreman_request import run_foreman_happy_path

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class DemoResponse(BaseModel):
    ok: bool = True
    skill_run_id: str
    final_state: str
    status: str
    history: list[str]
    tool_calls: list[dict] = Field(default_factory=list)
    telegram_sent: list[dict] = Field(default_factory=list)


@router.post("/demo", response_model=DemoResponse)
def runtime_demo() -> DemoResponse:
    """In-memory foreman happy-path demo (no persistence)."""
    from scenarios.foreman_request import get_telegram_stub

    router_rt, results = run_foreman_happy_path()
    last = results[-1]
    all_calls: list[dict] = []
    for result in results:
        all_calls.extend(result.trace.tool_calls)

    return DemoResponse(
        skill_run_id=last.run.id,
        final_state=last.run.current_state,
        status=last.run.status.value,
        history=list(last.run.history),
        tool_calls=all_calls,
        telegram_sent=list(get_telegram_stub(router_rt).sent),
    )
