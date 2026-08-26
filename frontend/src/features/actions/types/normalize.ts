import type { ActionDef, ActionRecipeStep } from "@/features/actions/types/action";
import { createId } from "@/shared/utils/id";

const ACTION_ID_PATTERN = /^[a-z][a-z0-9_]*$/;

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

export function createRecipeStep(
  partial?: Partial<ActionRecipeStep>,
): ActionRecipeStep {
  return {
    id: partial?.id ?? createId(),
    tool: partial?.tool?.trim() ?? "",
    command: partial?.command?.trim() ?? "",
    args: partial?.args ?? "",
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
  const record = raw as Partial<ActionRecipeStep>;
  return createRecipeStep({
    id: record.id,
    tool: record.tool ?? "",
    command: record.command ?? "",
    args: typeof record.args === "string" ? record.args : "",
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

  return {
    id,
    name: record.name?.trim() || id,
    description: record.description ?? "",
    recipe,
    createdAt: record.createdAt || now,
    updatedAt: record.updatedAt || now,
  };
}

export function createEmptyAction(partial: Partial<ActionDef> & { name: string }): ActionDef {
  const now = new Date().toISOString();
  const name = partial.name.trim() || "action";
  const id = normalizeActionId(partial.id || name);
  return {
    id: id || `action_${createId().slice(0, 6)}`,
    name,
    description: partial.description ?? "",
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
