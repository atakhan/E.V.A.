import type { ToolApiLog } from "@/features/tools/services/toolLogsApi";

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function formatLogTime(value: string): string {
  return new Date(value).toLocaleString();
}

export function logPreview(log: ToolApiLog): string {
  const preview = asString(log.requestSummary.preview);
  if (preview) return preview;

  const legacyPreview = asString(log.requestSummary.promptPreview);
  if (legacyPreview) return legacyPreview;

  const input = asRecord(log.requestSummary.input);
  for (const key of ["text", "prompt", "query"]) {
    const value = asString(input?.[key]);
    if (value) return value.length > 240 ? `${value.slice(0, 239)}…` : value;
  }

  const data = asRecord(log.responseSummary.data);
  const text = asString(data?.text);
  if (text) return text.length > 240 ? `${text.slice(0, 239)}…` : text;

  return `${log.toolId}.${log.command}`;
}

export function logUsageLabel(log: ToolApiLog): string | null {
  const usage = log.usage;
  const total = usage.total_tokens;
  const prompt = usage.prompt_tokens;
  const completion = usage.completion_tokens;

  if (typeof total === "number") {
    return `${total} tok`;
  }
  if (typeof prompt === "number" || typeof completion === "number") {
    return `${prompt ?? 0}+${completion ?? 0} tok`;
  }
  return null;
}

export function logStatusCode(log: ToolApiLog): number | null {
  const data = asRecord(log.responseSummary.data);
  const sent = asRecord(data?.sent);
  const code = data?.statusCode ?? sent?.statusCode;
  return typeof code === "number" ? code : null;
}

export function shortCredentialId(id: string | null | undefined): string | null {
  if (!id) return null;
  return id.length > 10 ? `${id.slice(0, 8)}…` : id;
}

export function shortSkillRunId(id: string | null | undefined): string | null {
  if (!id) return null;
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}
