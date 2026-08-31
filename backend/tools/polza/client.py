from __future__ import annotations

from typing import Any

import httpx


class PolzaApiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PolzaClient:
    def __init__(self, api_key: str, base_url: str = "https://polza.ai/api/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key and api_key != "anonymous":
            self._headers["Authorization"] = f"Bearer {api_key}"

    def get_balance(self) -> dict[str, Any]:
        return self._request("GET", "/balance")

    def list_models(self, *, model_type: str = "chat") -> list[dict[str, Any]]:
        body = self._request("GET", "/models", params={"type": model_type})
        data = body.get("data")
        return data if isinstance(data, list) else []

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        return self._request("POST", "/chat/completions", json=payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers,
                params=params,
                json=json,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise PolzaApiError(f"Polza API network error: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text
            try:
                parsed = response.json()
                if isinstance(parsed, dict):
                    detail = str(parsed.get("error", {}).get("message", detail))
            except ValueError:
                pass
            raise PolzaApiError(detail or f"HTTP {response.status_code}", status_code=response.status_code)

        if not response.content:
            return {}
        body = response.json()
        return body if isinstance(body, dict) else {"data": body}
