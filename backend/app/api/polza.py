from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from definition.services.agent_service import AgentService
from definition.services.tool_api_log_service import ToolApiLogService
from infrastructure.crypto.secrets import decrypt_secret
from infrastructure.models.tables import AgentRow, ToolCredentialRow
from tools.polza import PolzaApiError, PolzaClient

router = APIRouter(prefix="/api/agents/{slug}/tools/polza_ai_llm", tags=["polza"])


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


class PolzaBalanceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: str
    credential_id: str = Field(alias="credentialId")


class PolzaModelItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    type: str = "chat"
    context_length: int | None = Field(default=None, alias="contextLength")


def _require_agent(session: Session, slug: str) -> AgentRow:
    agent = session.scalar(select(AgentRow).where(AgentRow.slug == slug))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


from runtime.tool_instance_resolver import instances_by_type


def _bound_polza_credential_id(
    session: Session,
    slug: str,
    instance_id: str | None = None,
) -> str | None:
    agent_doc = AgentService(session).get_agent_by_slug(slug)
    if not agent_doc:
        return None
    if instance_id:
        for binding in agent_doc.get("tools", []):
            if binding.get("id") == instance_id and binding.get("credentialId"):
                return str(binding["credentialId"])
        return None
    polza_instances = instances_by_type(agent_doc, "polza_ai_llm", enabled_only=True)
    if len(polza_instances) == 1 and polza_instances[0].get("credentialId"):
        return str(polza_instances[0]["credentialId"])
    for binding in agent_doc.get("tools", []):
        if binding.get("toolId") == "polza_ai_llm" and binding.get("credentialId"):
            return str(binding["credentialId"])
    return None


def _resolve_polza_credential(
    session: Session,
    slug: str,
    credential_id: str | None,
    instance_id: str | None = None,
) -> ToolCredentialRow:
    agent = _require_agent(session, slug)
    resolved_id = credential_id or _bound_polza_credential_id(session, slug, instance_id)

    query = select(ToolCredentialRow).where(
        ToolCredentialRow.agent_id == agent.id,
        ToolCredentialRow.tool_id == "polza_ai_llm",
    )
    if resolved_id:
        query = query.where(ToolCredentialRow.id == resolved_id)

    row = session.scalar(query.order_by(ToolCredentialRow.created_at.desc()).limit(1))
    if row is None:
        raise HTTPException(status_code=404, detail="Polza credential not found")
    return row


def _client_for_row(row: ToolCredentialRow) -> PolzaClient:
    secret = decrypt_secret(row.secret_encrypted)
    api_key = secret.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key missing in credential")
    settings = get_settings()
    return PolzaClient(str(api_key), base_url=settings.polza_api_base)


@router.get("/models", response_model=list[PolzaModelItem])
def list_polza_models(
    slug: str,
    credential_id: str | None = Query(default=None, alias="credentialId"),
    session: Session = Depends(_db_session),
) -> list[dict[str, Any]]:
    _require_agent(session, slug)
    settings = get_settings()

    models: list[dict[str, Any]] = []
    try:
        row = _resolve_polza_credential(session, slug, credential_id)
        models = _client_for_row(row).list_models(model_type="chat")
    except (HTTPException, PolzaApiError):
        try:
            # Public catalog — no key required per Polza docs
            models = PolzaClient("anonymous", base_url=settings.polza_api_base).list_models(
                model_type="chat"
            )
        except PolzaApiError as exc:
            raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    result: list[dict[str, Any]] = []
    for model in models:
        if not isinstance(model, dict) or not model.get("id"):
            continue
        top = model.get("top_provider") if isinstance(model.get("top_provider"), dict) else {}
        context_length = top.get("context_length") if isinstance(top, dict) else None
        if context_length is None:
            context_length = model.get("context_length")
        result.append(
            {
                "id": model["id"],
                "name": model.get("name") or model["id"],
                "type": model.get("type") or "chat",
                "contextLength": context_length if isinstance(context_length, int) else None,
            }
        )
    return result


@router.get("/balance", response_model=PolzaBalanceResponse)
def get_polza_balance(
    slug: str,
    credential_id: str | None = Query(default=None, alias="credentialId"),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    row = _resolve_polza_credential(session, slug, credential_id)
    client = _client_for_row(row)
    try:
        balance = client.get_balance()
    except PolzaApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    amount = balance.get("amount")
    meta = dict(row.meta or {})
    meta["balance_amount"] = str(amount) if amount is not None else None
    row.meta = meta
    session.flush()

    return {
        "amount": str(amount) if amount is not None else "0",
        "credentialId": row.id,
    }


@router.get("/logs")
def list_polza_logs(
    slug: str,
    credential_id: str | None = Query(default=None, alias="credentialId"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(_db_session),
) -> list[dict[str, Any]]:
    agent = _require_agent(session, slug)
    return ToolApiLogService(session).list_logs(
        agent.id,
        tool_id="polza_ai_llm",
        credential_id=credential_id,
        limit=limit,
    )["items"]
