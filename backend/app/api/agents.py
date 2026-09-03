from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.agent_http import raise_agent_service_error
from app.deps import get_agent_service
from definition.schemas.agent_api import (
    AgentApi,
    AgentArchiveResponseApi,
    AgentCreateRequest,
    AgentPublicationApi,
    AgentSummaryApi,
    AgentValidationReportApi,
    PublishResponseApi,
)
from definition.services.agent_service import AgentArchivedError, AgentService

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


@router.get("", response_model=list[AgentSummaryApi])
def list_agents(
    include_archived: bool = Query(default=False, alias="includeArchived"),
    session: Session = Depends(_db_session),
) -> list[dict[str, Any]]:
    service = get_agent_service(session)
    return service.list_agents(include_archived=include_archived)


@router.post("", response_model=AgentApi, status_code=201)
def create_agent(
    payload: AgentCreateRequest,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    service = get_agent_service(session)
    try:
        return service.create_agent(
            name=payload.name,
            slug=payload.slug.strip().lower(),
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{slug}", response_model=AgentApi)
def get_agent(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    service = get_agent_service(session)
    agent = service.get_agent_by_slug(slug)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{slug}", response_model=AgentApi)
def upsert_agent(
    slug: str,
    payload: dict[str, Any],
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    service = get_agent_service(session)
    try:
        return service.upsert_draft(slug, payload)
    except (AgentArchivedError, KeyError) as exc:
        raise_agent_service_error(exc)


@router.delete("/{slug}", status_code=204, response_class=Response)
def delete_agent(slug: str, session: Session = Depends(_db_session)) -> Response:
    service = get_agent_service(session)
    try:
        service.delete_agent(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/{slug}/validate", response_model=AgentValidationReportApi)
def validate_agent_endpoint(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    service = get_agent_service(session)
    try:
        return service.validate_draft(slug)
    except (AgentArchivedError, KeyError) as exc:
        raise_agent_service_error(exc)


@router.post("/{slug}/archive", response_model=AgentArchiveResponseApi)
def archive_agent(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    service = get_agent_service(session)
    try:
        summary = service.archive_agent(slug)
    except KeyError as exc:
        raise_agent_service_error(exc)
    return {
        "ok": True,
        "slug": summary["slug"],
        "archivedAt": summary["archivedAt"],
    }


@router.post("/{slug}/unarchive", response_model=AgentArchiveResponseApi)
def unarchive_agent(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    service = get_agent_service(session)
    try:
        summary = service.unarchive_agent(slug)
    except KeyError as exc:
        raise_agent_service_error(exc)
    return {
        "ok": True,
        "slug": summary["slug"],
        "archivedAt": summary["archivedAt"],
    }


@router.post("/{slug}/publish", response_model=PublishResponseApi)
def publish_agent(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    service = get_agent_service(session)
    try:
        return service.publish(slug)
    except (AgentArchivedError, KeyError) as exc:
        raise_agent_service_error(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{slug}/publications", response_model=list[AgentPublicationApi])
def list_publications(slug: str, session: Session = Depends(_db_session)) -> list[dict[str, Any]]:
    service = get_agent_service(session)
    try:
        return service.list_publications(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
