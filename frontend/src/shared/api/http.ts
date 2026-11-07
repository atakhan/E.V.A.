export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type UnauthorizedHandler = () => void;

let onUnauthorized: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path.startsWith("/api") ? path : `/api${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (response.status === 401) {
    onUnauthorized?.();
    const detail = await response.text();
    const path = window.location.pathname;
    if (path !== "/login" && path !== "/register") {
      const next = encodeURIComponent(`${path}${window.location.search}`);
      window.location.assign(`/login?next=${next}`);
    }
    throw new ApiError(401, detail || "Authentication required");
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
