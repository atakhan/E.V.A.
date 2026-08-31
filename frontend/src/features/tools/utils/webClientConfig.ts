export interface WebClientBindingConfig {
  healthPath?: string;
  sendMessagePath?: string;
  getSnapshotPath?: string;
  authStyle?: "bearer" | "x-api-key";
  timeoutSec?: number;
}

export const WEB_CLIENT_DEFAULTS: Required<WebClientBindingConfig> = {
  healthPath: "/eva/health",
  sendMessagePath: "/eva/messages",
  getSnapshotPath: "/eva/context",
  authStyle: "bearer",
  timeoutSec: 30,
};

export function parseWebClientConfigNote(raw: string | undefined | null): WebClientBindingConfig {
  const text = (raw ?? "").trim();
  if (!text) return { ...WEB_CLIENT_DEFAULTS };
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as WebClientBindingConfig;
      return { ...WEB_CLIENT_DEFAULTS, ...parsed };
    } catch {
      return { ...WEB_CLIENT_DEFAULTS };
    }
  }
  return { ...WEB_CLIENT_DEFAULTS };
}

export function serializeWebClientConfigNote(config: WebClientBindingConfig): string {
  return JSON.stringify({ ...WEB_CLIENT_DEFAULTS, ...config });
}
