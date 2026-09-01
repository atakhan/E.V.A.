import type { ToolFieldDef } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { validateFields } from "@/shared/schema/fieldSchema";

export function getConfigSchema(toolTypeId: string): ToolFieldDef[] {
  return getToolDefinition(toolTypeId)?.configSchema ?? [];
}

export function mergeConfigDefaults(
  toolTypeId: string,
  config: Record<string, unknown> | undefined,
): Record<string, unknown> {
  const merged: Record<string, unknown> = {};
  for (const field of getConfigSchema(toolTypeId)) {
    if (field.default !== undefined) merged[field.id] = field.default;
  }
  if (config) Object.assign(merged, config);
  return merged;
}

export function validateInstanceConfig(toolTypeId: string, config: Record<string, unknown>): string[] {
  return validateFields(getConfigSchema(toolTypeId), config, "config.").errors;
}
