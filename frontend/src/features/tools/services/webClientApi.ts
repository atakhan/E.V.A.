import type { PolzaApiLog } from "@/features/tools/services/credentialsApi";

export interface WebClientIntegrationInfo {
  ingressUrl: string;
  outboxUrlTemplate: string;
  inboundApiKeyHint: string;
  outboundBaseUrl: string;
  outboundBaseUrlDocker: string;
  paths: Record<string, unknown>;
  localDevHints: Record<string, string>;
}

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchWebClientIntegration(
  agentSlug: string,
  credentialId: string,
): Promise<WebClientIntegrationInfo> {
  return request(
    `/agents/${encodeURIComponent(agentSlug)}/tools/web_client/integration?credentialId=${encodeURIComponent(credentialId)}`,
  );
}

export async function fetchWebClientLogs(
  agentSlug: string,
  credentialId?: string,
): Promise<PolzaApiLog[]> {
  const query = credentialId ? `?credentialId=${encodeURIComponent(credentialId)}` : "";
  return request(`/agents/${encodeURIComponent(agentSlug)}/tools/web_client/logs${query}`);
}

export async function generateInboundKey(agentSlug: string): Promise<string> {
  const body = await request<{ inboundApiKey: string }>(
    `/agents/${encodeURIComponent(agentSlug)}/tools/web_client/generate-inbound-key`,
    { method: "POST" },
  );
  return body.inboundApiKey;
}
