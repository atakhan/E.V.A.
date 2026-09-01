import type { ToolFieldDef, ToolFieldType } from "@/features/tools/types/tool";

export const VALID_FIELD_TYPES: ToolFieldType[] = [
  "string",
  "template",
  "text",
  "integer",
  "boolean",
  "enum",
  "json",
  "string_array",
];

export function coerceFieldValue(field: ToolFieldDef, raw: unknown): unknown {
  const fieldType = field.type ?? "string";
  if (raw == null) return null;
  if (fieldType === "string" || fieldType === "template" || fieldType === "text") {
    return String(raw);
  }
  if (fieldType === "integer") {
    if (typeof raw === "boolean") throw new Error("boolean is not integer");
    if (typeof raw === "number") return raw;
    const text = String(raw).trim();
    if (!text) return null;
    return Number(text);
  }
  if (fieldType === "boolean") {
    if (typeof raw === "boolean") return raw;
    const lowered = String(raw).trim().toLowerCase();
    if (lowered === "true" || lowered === "1" || lowered === "yes") return true;
    if (lowered === "false" || lowered === "0" || lowered === "") return false;
    return Boolean(raw);
  }
  if (fieldType === "enum") return String(raw);
  if (fieldType === "json") {
    if (typeof raw === "object") return raw;
    if (typeof raw === "string") return JSON.parse(raw);
    return raw;
  }
  if (fieldType === "string_array") {
    if (Array.isArray(raw)) return raw.map(String);
    if (typeof raw === "string") {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.map(String);
    }
    throw new Error("expected string array");
  }
  return raw;
}

export function applyDefaults(
  schema: ToolFieldDef[],
  data: Record<string, unknown> | undefined,
): Record<string, unknown> {
  const merged: Record<string, unknown> = {};
  for (const field of schema) {
    if (field.default !== undefined) merged[field.id] = field.default;
  }
  if (data) Object.assign(merged, data);
  return merged;
}

export function validateFields(
  schema: ToolFieldDef[],
  data: Record<string, unknown> | undefined,
  prefix = "",
): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  const payload = data ?? {};
  const known = new Set(schema.map((field) => field.id));

  for (const field of schema) {
    const label = prefix ? `${prefix}${field.id}` : field.id;
    const value = payload[field.id];
    if (field.required && (value === undefined || value === "")) {
      errors.push(`${label} is required`);
      continue;
    }
    if (value === undefined) continue;
    try {
      const coerced = coerceFieldValue(field, value);
      if (field.type === "enum" && field.enum && !field.enum.includes(String(coerced))) {
        errors.push(`${label} must be one of ${field.enum.join(", ")}`);
      }
      if (field.type === "integer" && typeof coerced !== "number") {
        errors.push(`${label} must be integer`);
      }
      if (field.type === "boolean" && typeof coerced !== "boolean") {
        errors.push(`${label} must be boolean`);
      }
    } catch (error) {
      errors.push(`${label}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  for (const key of Object.keys(payload)) {
    if (!known.has(key)) warnings.push(`${prefix}${key}: unknown field`);
  }

  return { errors, warnings };
}

export function objectToFieldValues(
  schema: ToolFieldDef[],
  input: Record<string, unknown>,
): Record<string, string> {
  const values: Record<string, string> = {};
  for (const field of schema) {
    const raw = input[field.id];
    if (raw == null) {
      values[field.id] = "";
      continue;
    }
    if ((field.type === "json" || field.type === "string_array") && typeof raw === "object") {
      values[field.id] = JSON.stringify(raw, null, 2);
    } else {
      values[field.id] = String(raw);
    }
  }
  return values;
}

export function fieldValuesToObject(
  schema: ToolFieldDef[],
  values: Record<string, string>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of schema) {
    const raw = values[field.id] ?? "";
    if (!raw.trim() && field.default !== undefined) {
      result[field.id] = field.default;
      continue;
    }
    if (!raw.trim()) continue;
    if (field.type === "json" || field.type === "string_array") {
      try {
        result[field.id] = JSON.parse(raw);
      } catch {
        result[field.id] = raw;
      }
    } else if (field.type === "integer") {
      result[field.id] = Number(raw);
    } else if (field.type === "boolean") {
      result[field.id] = coerceFieldValue(field, raw);
    } else {
      result[field.id] = raw;
    }
  }
  return result;
}

export function genericFieldsFromInput(input: Record<string, unknown>): ToolFieldDef[] {
  return Object.keys(input).map((key) => ({
    id: key,
    type: typeof input[key] === "object" ? "json" : "template",
    scope: "call",
    ui: { label: key },
  }));
}
