import type { ActionDef, ActionPolicy, ActionRecipeStep } from "@/features/actions/types/action";
import { createId } from "@/shared/utils/id";

const ACTION_ID_PATTERN = /^[a-z][a-z0-9_]*$/;
const SEMVER_PATTERN = /^\d+\.\d+\.\d+$/;
export const DEFAULT_ACTION_VERSION = "0.1.0";
export const DEFAULT_ACTION_POLICY: ActionPolicy = "auto";

export function normalizeActionId(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 64);
}

export function isValidActionId(id: string): boolean {
  return id.length >= 2 && ACTION_ID_PATTERN.test(id);
}

export function isValidActionVersion(version: string): boolean {
  return SEMVER_PATTERN.test(version.trim());
}

function parseJsonObject(raw: unknown): Record<string, unknown> {
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    return { ...(raw as Record<string, unknown>) };
  }
  if (typeof raw === "string") {
    const text = raw.trim();
    if (!text) return {};
    try {
      const parsed = JSON.parse(text) as unknown;
      return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  return {};
}

function normalizePolicy(raw: unknown): ActionPolicy {
  return raw === "needs_human" ? "needs_human" : DEFAULT_ACTION_POLICY;
}

function normalizeStepInput(raw: unknown): Record<string, unknown> {
  if (typeof raw === "object" && raw !== null && !Array.isArray(raw)) {
    return { ...(raw as Record<string, unknown>) };
  }
  if (typeof raw === "string") {
    return parseJsonObject(raw);
  }
  return {};
}

export function createRecipeStep(
  partial?: Partial<ActionRecipeStep>,
): ActionRecipeStep {
  return {
    id: partial?.id ?? createId(),
    tool: partial?.tool?.trim() ?? "",
    command: partial?.command?.trim() ?? "",
    input: normalizeStepInput(partial?.input),
    when: partial?.when?.trim() || undefined,
  };
}

function normalizeStep(raw: unknown): ActionRecipeStep | null {
  if (typeof raw === "string") {
    const value = raw.trim();
    if (!value) return null;
    const dot = value.indexOf(".");
    if (dot > 0) {
      return createRecipeStep({
        tool: value.slice(0, dot),
        command: value.slice(dot + 1),
      });
    }
    return createRecipeStep({ tool: "", command: value });
  }

  if (typeof raw !== "object" || raw === null) return null;
  const record = raw as Partial<ActionRecipeStep> & { args?: unknown };
  const input =
    record.input !== undefined
      ? normalizeStepInput(record.input)
      : normalizeStepInput(record.args);

  return createRecipeStep({
    id: record.id,
    tool: record.tool ?? "",
    command: record.command ?? "",
    input,
    when: record.when,
  });
}

export function normalizeAction(raw: unknown): ActionDef | null {
  if (typeof raw !== "object" || raw === null) return null;
  const record = raw as Partial<ActionDef> & { recipe?: unknown };

  const id = normalizeActionId(record.id || record.name || "");
  if (!id) return null;

  const now = new Date().toISOString();
  const recipeRaw = Array.isArray(record.recipe) ? record.recipe : [];
  const recipe = recipeRaw
    .map((step) => normalizeStep(step))
    .filter((step): step is ActionRecipeStep => step !== null);

  const version = (record.version || DEFAULT_ACTION_VERSION).trim() || DEFAULT_ACTION_VERSION;

  return {
    id,
    name: record.name?.trim() || id,
    description: record.description ?? "",
    version: isValidActionVersion(version) ? version : DEFAULT_ACTION_VERSION,
    policy: normalizePolicy(record.policy),
    inputSchema: parseJsonObject(record.inputSchema),
    outputSchema: parseJsonObject(record.outputSchema),
    recipe,
    createdAt: record.createdAt || now,
    updatedAt: record.updatedAt || now,
  };
}

export function createEmptyAction(partial: Partial<ActionDef> & { name: string }): ActionDef {
  const now = new Date().toISOString();
  const name = partial.name.trim() || "action";
  const id = normalizeActionId(partial.id || name);
  const version = (partial.version || DEFAULT_ACTION_VERSION).trim() || DEFAULT_ACTION_VERSION;

  return {
    id: id || `action_${createId().slice(0, 6)}`,
    name,
    description: partial.description ?? "",
    version: isValidActionVersion(version) ? version : DEFAULT_ACTION_VERSION,
    policy: normalizePolicy(partial.policy),
    inputSchema: parseJsonObject(partial.inputSchema),
    outputSchema: parseJsonObject(partial.outputSchema),
    recipe: Array.isArray(partial.recipe)
      ? partial.recipe.map((step) => createRecipeStep(step))
      : [],
    createdAt: partial.createdAt ?? now,
    updatedAt: partial.updatedAt ?? now,
  };
}

export function formatRecipeStepLabel(step: ActionRecipeStep): string {
  if (step.tool && step.command) return `${step.tool}.${step.command}`;
  return step.command || step.tool || "(пустой шаг)";
}

export function formatStepInput(step: ActionRecipeStep): string {
  const keys = Object.keys(step.input);
  if (keys.length === 0) return "";
  return JSON.stringify(step.input, null, 2);
}

export function parseStepInput(text: string): Record<string, unknown> {
  const trimmed = text.trim();
  if (!trimmed) return {};
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

export function formatJsonSchema(schema: Record<string, unknown>): string {
  if (Object.keys(schema).length === 0) return "";
  return JSON.stringify(schema, null, 2);
}

export function parseJsonSchema(text: string): Record<string, unknown> {
  return parseJsonObject(text);
}
