import type { ToolInstance } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";

const CREDENTIAL_TYPES = new Set(["telegram", "polza_ai_llm", "web_client"]);

export function instanceTypeName(instance: ToolInstance): string {
  return getToolDefinition(instance.toolId)?.name ?? instance.toolId;
}

export function instanceStatusBadge(instance: ToolInstance): { label: string; class: string } {
  if (!instance.enabled) return { label: "off", class: "badge-ghost" };
  if (!instance.credentialId && CREDENTIAL_TYPES.has(instance.toolId)) {
    return { label: "no cred", class: "badge-warning" };
  }
  return { label: "on", class: "badge-success" };
}
