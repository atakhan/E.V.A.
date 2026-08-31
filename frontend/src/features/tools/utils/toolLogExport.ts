import type { ToolApiLog } from "@/features/tools/services/toolLogsApi";
import { logPreview } from "@/features/tools/utils/toolLogFormat";

function downloadBlob(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function csvEscape(value: unknown): string {
  const text = value == null ? "" : String(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function downloadToolLogsJson(agentSlug: string, logs: ToolApiLog[]) {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  downloadBlob(
    `${agentSlug}-tool-logs-${stamp}.json`,
    JSON.stringify({ exportedAt: new Date().toISOString(), count: logs.length, items: logs }, null, 2),
    "application/json;charset=utf-8",
  );
}

export function downloadToolLogsCsv(agentSlug: string, logs: ToolApiLog[]) {
  const headers = [
    "id",
    "createdAt",
    "toolId",
    "command",
    "status",
    "durationMs",
    "model",
    "actionId",
    "skillRunId",
    "credentialId",
    "errorMessage",
    "preview",
    "requestSummary",
    "responseSummary",
    "usage",
  ];
  const rows = logs.map((log) =>
    [
      log.id,
      log.createdAt,
      log.toolId,
      log.command,
      log.status,
      log.durationMs ?? "",
      log.model ?? "",
      log.actionId ?? "",
      log.skillRunId ?? "",
      log.credentialId ?? "",
      log.errorMessage ?? "",
      logPreview(log),
      JSON.stringify(log.requestSummary),
      JSON.stringify(log.responseSummary),
      JSON.stringify(log.usage),
    ]
      .map(csvEscape)
      .join(","),
  );
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  downloadBlob(
    `${agentSlug}-tool-logs-${stamp}.csv`,
    [headers.join(","), ...rows].join("\n"),
    "text/csv;charset=utf-8",
  );
}
