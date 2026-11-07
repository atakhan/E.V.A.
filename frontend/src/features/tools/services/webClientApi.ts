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

import { apiRequest } from "@/shared/api/http";

export async function fetchWebClientIntegration(
  agentSlug: string,
  credentialId: string,
): Promise<WebClientIntegrationInfo> {
  return apiRequest(
    `/agents/${encodeURIComponent(agentSlug)}/tools/web_client/integration?credentialId=${encodeURIComponent(credentialId)}`,
  );
}

export async function fetchWebClientLogs(
  agentSlug: string,
  credentialId?: string,
): Promise<PolzaApiLog[]> {
  const query = credentialId ? `?credentialId=${encodeURIComponent(credentialId)}` : "";
  return apiRequest(`/agents/${encodeURIComponent(agentSlug)}/tools/web_client/logs${query}`);
}

export async function generateInboundKey(agentSlug: string): Promise<string> {
  const body = await apiRequest<{ inboundApiKey: string }>(
    `/agents/${encodeURIComponent(agentSlug)}/tools/web_client/generate-inbound-key`,
    { method: "POST" },
  );
  return body.inboundApiKey;
}
