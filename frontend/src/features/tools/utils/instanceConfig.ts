import type { ToolConfigFieldDef } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";

export function getConfigSchema(toolTypeId: string): ToolConfigFieldDef[] {
  return getToolDefinition(toolTypeId)?.configSchema ?? [];
}

export function mergeConfigDefaults(
  toolTypeId: string,
  config: Record<string, unknown> | undefined,
): Record<string, unknown> {
  const merged: Record<string, unknown> = {};
  for (const field of getConfigSchema(toolTypeId)) {
    if (field.default !== undefined) {
      merged[field.id] = field.default;
    }
  }
  if (config) Object.assign(merged, config);
  return merged;
}

export function validateInstanceConfig(
  toolTypeId: string,
  config: Record<string, unknown>,
): string[] {
  const errors: string[] = [];
  for (const field of getConfigSchema(toolTypeId)) {
    const value = config[field.id];
    if (field.required && (value === undefined || value === "")) {
      errors.push(`${field.id} обязателен`);
      continue;
    }
    if (value === undefined) continue;
    if (field.type === "integer" && typeof value !== "number") {
      errors.push(`${field.id} должен быть числом`);
    }
    if (field.type === "boolean" && typeof value !== "boolean") {
      errors.push(`${field.id} должен быть boolean`);
    }
    if (field.type === "enum" && field.enum && !field.enum.includes(String(value))) {
      errors.push(`${field.id} недопустимое значение`);
    }
  }
  return errors;
}
