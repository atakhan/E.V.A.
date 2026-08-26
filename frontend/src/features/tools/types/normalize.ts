import type { ToolBinding } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { createId } from "@/shared/utils/id";

export function createToolBinding(
  toolId: string,
  partial?: Partial<ToolBinding>,
): ToolBinding {
  return {
    id: partial?.id ?? createId(),
    toolId,
    enabled: partial?.enabled ?? true,
    credentialId: partial?.credentialId,
    configNote: partial?.configNote ?? "",
  };
}

export function normalizeToolBinding(raw: unknown): ToolBinding | null {
  if (typeof raw !== "object" || raw === null) return null;
  const record = raw as Partial<ToolBinding>;
  const toolId = String(record.toolId || "").trim();
  if (!toolId || !getToolDefinition(toolId)) return null;

  return {
    id: record.id || createId(),
    toolId,
    enabled: record.enabled !== false,
    credentialId:
      typeof record.credentialId === "string" && record.credentialId.trim()
        ? record.credentialId.trim()
        : undefined,
    configNote:
      typeof record.configNote === "string"
        ? record.configNote
        : typeof (record as { config?: unknown }).config === "string"
          ? String((record as { config: string }).config)
          : "",
  };
}
