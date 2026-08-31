import type { ToolInstance } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";

function parseLegacyConfig(raw: unknown): Record<string, unknown> {
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    return { ...(raw as Record<string, unknown>) };
  }
  const text = String(raw ?? "").trim();
  if (!text) return {};
  if (text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text) as unknown;
      return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return { note: text };
    }
  }
  return { note: text };
}

export function createToolInstance(
  toolId: string,
  partial?: Partial<ToolInstance>,
): ToolInstance {
  const typeDef = getToolDefinition(toolId);
  const defaultName = typeDef?.name ?? toolId;
  const config = partial?.config ?? parseLegacyConfig(partial?.configNote);
  return {
    id: partial?.id ?? toolId,
    toolId,
    name: partial?.name?.trim() || defaultName,
    enabled: partial?.enabled ?? true,
    credentialId: partial?.credentialId,
    config,
  };
}

export function normalizeToolInstance(raw: unknown): ToolInstance | null {
  if (typeof raw !== "object" || raw === null) return null;
  const record = raw as Partial<ToolInstance> & { configNote?: string };
  const toolId = String(record.toolId || "").trim();
  if (!toolId || !getToolDefinition(toolId)) return null;

  const config =
    record.config && typeof record.config === "object"
      ? { ...record.config }
      : parseLegacyConfig(record.configNote);

  const typeDef = getToolDefinition(toolId);
  return {
    id: String(record.id || toolId).trim() || toolId,
    toolId,
    name: String(record.name || typeDef?.name || toolId).trim(),
    enabled: record.enabled !== false,
    credentialId:
      typeof record.credentialId === "string" && record.credentialId.trim()
        ? record.credentialId.trim()
        : undefined,
    config,
  };
}

/** @deprecated use normalizeToolInstance */
export const normalizeToolBinding = normalizeToolInstance;

/** @deprecated use createToolInstance */
export const createToolBinding = createToolInstance;
