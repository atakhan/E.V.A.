from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import db_session, require_user
from definition.services.auth_service import AuthService, user_to_api
from infrastructure.models.tables import UserRow

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthCredentialsRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class UserApi(BaseModel):
    id: str
    email: str


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_ttl_hours * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_cookie_name, path="/")


@router.post("/register", response_model=UserApi, status_code=201)
def register(
    payload: AuthCredentialsRequest,
    response: Response,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    service = AuthService(session)
    try:
        user = service.register(email=payload.email, password=payload.password)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    auth_session = service.create_session(user)
    _set_session_cookie(response, auth_session.id)
    return user_to_api(user)


@router.post("/login", response_model=UserApi)
def login(
    payload: AuthCredentialsRequest,
    response: Response,
    session: Session = Depends(db_session),
) -> dict[str, Any]:
    service = AuthService(session)
    try:
        user = service.authenticate(email=payload.email, password=payload.password)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    auth_session = service.create_session(user)
    _set_session_cookie(response, auth_session.id)
    return user_to_api(user)


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(db_session),
) -> Response:
    settings = get_settings()
    AuthService(session).revoke_session(request.cookies.get(settings.auth_cookie_name))
    _clear_session_cookie(response)
    return Response(status_code=204)


@router.get("/me", response_model=UserApi)
def me(user: UserRow = Depends(require_user)) -> dict[str, Any]:
    return user_to_api(user)
