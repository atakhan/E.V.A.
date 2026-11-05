from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.deps import session_scope
from definition.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _db_session():
    with session_scope() as session:
        yield session


class ProjectAgentApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_slug: str = Field(alias="agentSlug")
    origin_slug: str | None = Field(default=None, alias="originSlug")
    x: float = 0
    y: float = 0


class ProjectApi(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    slug: str
    name: str
    description: str = ""
    agents: list[ProjectAgentApi] = Field(default_factory=list)
    runtime_agent_slug: str | None = Field(default=None, alias="runtimeAgentSlug")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class ProjectCreateRequest(BaseModel):
    name: str
    slug: str
    description: str = ""


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    agents: list[ProjectAgentApi] | None = None


def _service(session: Session) -> ProjectService:
    return ProjectService(session)


@router.get("", response_model=list[ProjectApi])
def list_projects(session: Session = Depends(_db_session)) -> list[dict[str, Any]]:
    return _service(session).list_projects()


@router.post("", response_model=ProjectApi, status_code=201)
def create_project(payload: ProjectCreateRequest, session: Session = Depends(_db_session)) -> dict[str, Any]:
    try:
        return _service(session).create_project(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{slug}", response_model=ProjectApi)
def get_project(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    project = _service(session).get_by_slug(slug)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{slug}", response_model=ProjectApi)
def update_project(
    slug: str,
    payload: ProjectUpdateRequest,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    agents = None
    if payload.agents is not None:
        agents = [item.model_dump(by_alias=True) for item in payload.agents]
    try:
        return _service(session).update_project(
            slug,
            name=payload.name,
            description=payload.description,
            agents=agents,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{slug}", status_code=204, response_class=Response)
def delete_project(slug: str, session: Session = Depends(_db_session)) -> Response:
    try:
        _service(session).delete_project(slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return Response(status_code=204)
