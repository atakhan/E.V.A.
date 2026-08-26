from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from definition.services.credential_service import CredentialService

router = APIRouter(prefix="/api/agents", tags=["credentials"])


class CredentialCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool_id: str = Field(alias="toolId")
    name: str
    secret: dict[str, Any]


class CredentialPublicApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    tool_id: str = Field(alias="toolId")
    name: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


@router.get("/{slug}/credentials", response_model=list[CredentialPublicApi])
def list_credentials(
    slug: str,
    tool_id: str | None = None,
    session: Session = Depends(_db_session),
) -> list[dict[str, Any]]:
    service = CredentialService(session)
    try:
        return service.list_credentials(slug, tool_id=tool_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{slug}/credentials", response_model=CredentialPublicApi, status_code=201)
def create_credential(
    slug: str,
    payload: CredentialCreateRequest,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    service = CredentialService(session)
    try:
        return service.create_credential(
            slug,
            tool_id=payload.tool_id,
            name=payload.name,
            secret=payload.secret,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{slug}/credentials/{credential_id}", status_code=204, response_class=Response)
def delete_credential(
    slug: str,
    credential_id: str,
    session: Session = Depends(_db_session),
) -> Response:
    service = CredentialService(session)
    try:
        service.delete_credential(slug, credential_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/{slug}/credentials/{credential_id}/verify", response_model=CredentialPublicApi)
def verify_credential(
    slug: str,
    credential_id: str,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    service = CredentialService(session)
    try:
        return service.verify_telegram(slug, credential_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{slug}/credentials/{credential_id}/set-webhook")
def set_webhook(
    slug: str,
    credential_id: str,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    service = CredentialService(session)
    try:
        return service.set_telegram_webhook(slug, credential_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
