"""
Minimal web-app backend stub for local E.V.A. integration testing.

Run: uvicorn main:app --host 0.0.0.0 --port 8765
Or via docker-compose service `web-client-stub`.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Query

OUTBOUND_API_KEY = os.getenv("WEB_CLIENT_OUTBOUND_KEY", "dev-outbound-key")
EVA_INGRESS_URL = os.getenv("EVA_INGRESS_URL", "http://backend:8000/api/channels/web/foreman/events")
EVA_INBOUND_KEY = os.getenv("EVA_INBOUND_KEY", "")

app = FastAPI(title="E.V.A. Web Client Stub")

_sessions: dict[str, dict[str, Any]] = {}
_outbox: dict[str, list[dict[str, Any]]] = {}


def _auth(authorization: str | None = Header(default=None)) -> None:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif authorization:
        token = authorization.strip()
    if token != OUTBOUND_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid outbound API key")


@app.get("/eva/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "web-client-stub"}


@app.post("/eva/messages")
def receive_message(
    payload: dict[str, Any],
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _auth(authorization)
    session_id = str(payload.get("sessionId") or "")
    text = str(payload.get("text") or "")
    if not session_id:
        raise HTTPException(status_code=400, detail="sessionId required")
    _sessions.setdefault(session_id, {"sessionId": session_id})
    _sessions[session_id]["lastAgentMessage"] = text
    _sessions[session_id]["meta"] = payload.get("meta") or {}
    _outbox.setdefault(session_id, []).append({"text": text, "meta": payload.get("meta") or {}})
    return {"ok": True, "sessionId": session_id}


@app.get("/eva/context")
def get_context(
    sessionId: str = Query(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _auth(authorization)
    snapshot = _sessions.get(sessionId, {"sessionId": sessionId, "page": "/demo", "data": {}})
    return {"ok": True, **snapshot}


@app.post("/demo/send-to-eva")
async def demo_send_to_eva(payload: dict[str, Any]) -> dict[str, Any]:
    """Simulate user's Python backend forwarding a chat message to E.V.A."""
    if not EVA_INBOUND_KEY:
        raise HTTPException(status_code=400, detail="EVA_INBOUND_KEY is not configured")

    session_id = str(payload.get("sessionId") or "web:demo:local")
    text = str(payload.get("text") or "")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            EVA_INGRESS_URL,
            headers={"Authorization": f"Bearer {EVA_INBOUND_KEY}"},
            json={
                "sessionId": session_id,
                "type": "channel.message.received",
                "payload": {
                    "text": text,
                    "context": {"page": "/demo", "source": "web-client-stub"},
                },
            },
        )
    return {"ok": response.is_success, "status": response.status_code, "body": response.text}
