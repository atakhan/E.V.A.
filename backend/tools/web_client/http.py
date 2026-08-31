from __future__ import annotations

import time
from typing import Any

import httpx

from tools.web_client.config import resolve_backend_url


class WebClientHttpError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WebClientHttp:
    def __init__(
        self,
        *,
        base_url: str,
        outbound_api_key: str,
        config: dict[str, Any],
        docker_rewrite: bool = False,
        docker_host: str = "host.docker.internal",
    ) -> None:
        self.base_url = resolve_backend_url(base_url, docker_rewrite, docker_host).rstrip("/")
        self.outbound_api_key = outbound_api_key
        self.config = config
        self.timeout = float(config.get("timeoutSec") or 30)
        self.auth_style = str(config.get("authStyle") or "bearer").lower()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if not self.outbound_api_key:
            return headers
        if self.auth_style == "x-api-key":
            headers["X-Api-Key"] = self.outbound_api_key
        else:
            headers["Authorization"] = f"Bearer {self.outbound_api_key}"
        return headers

    def health(self) -> dict[str, Any]:
        path = str(self.config.get("healthPath") or "/eva/health")
        return self._request("GET", path)

    def send_message(self, *, session_id: str, text: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        path = str(self.config.get("sendMessagePath") or "/eva/messages")
        payload = {"sessionId": session_id, "text": text, "meta": meta or {}}
        return self._request("POST", path, json=payload)

    def get_snapshot(self, *, session_id: str) -> dict[str, Any]:
        path = str(self.config.get("getSnapshotPath") or "/eva/context")
        return self._request("GET", path, params={"sessionId": session_id})

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        started = time.perf_counter()
        try:
            response = httpx.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise WebClientHttpError(f"Web client network error: {exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        body: dict[str, Any] = {}
        if response.content:
            try:
                parsed = response.json()
                body = parsed if isinstance(parsed, dict) else {"data": parsed}
            except ValueError:
                body = {"raw": response.text}

        if response.status_code >= 400:
            detail = body.get("detail") or body.get("error") or response.text
            raise WebClientHttpError(str(detail) or f"HTTP {response.status_code}", status_code=response.status_code)

        body["_duration_ms"] = duration_ms
        body["_status_code"] = response.status_code
        return body
