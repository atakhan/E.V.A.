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

/** Schema form emits only known fields. Extra keys, such as an SSH command library, stay. */
export function mergeSchemaConfig(
  current: Record<string, unknown>,
  patch: Record<string, unknown>,
  schema: { id: string }[],
): Record<string, unknown> {
  const known = new Set(schema.map((field) => field.id));
  const extra: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(current)) {
    if (!known.has(key)) extra[key] = value;
  }
  return { ...extra, ...patch };
}
