import type { ActionDef, ActionRecipeStep } from "@/features/actions/types/action";
import type { Agent } from "@/features/agents/types/agent";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { resolveRecipeTool } from "@/features/tools/utils/resolveToolInstance";

export type ActionRecipeStatus = "ok" | "empty" | "tool_off" | "unknown";

export type RecipeStepStatus = "ok" | "disabled" | "unknown";

export function getRecipeStepStatus(
  agent: Pick<Agent, "tools">,
  step: ActionRecipeStep,
): RecipeStepStatus {
  if (!step.tool) return "unknown";
  const resolved = resolveRecipeTool(agent, step.tool);
  if (resolved.status === "unknown" || resolved.status === "ambiguous") return "unknown";
  if (resolved.status === "disabled") return "disabled";
  const def = getToolDefinition(resolved.typeId);
  if (!def) return "unknown";
  if (step.command && !def.commands.some((command) => command.id === step.command)) {
    return "unknown";
  }
  return "ok";
}

export function getActionRecipeStatus(
  agent: Pick<Agent, "tools">,
  action: ActionDef,
): ActionRecipeStatus {
  if (action.recipe.length === 0) return "empty";
  let hasToolOff = false;
  for (const step of action.recipe) {
    const status = getRecipeStepStatus(agent, step);
    if (status === "unknown") return "unknown";
    if (status === "disabled") hasToolOff = true;
  }
  return hasToolOff ? "tool_off" : "ok";
}

export function recipeStepSummary(agent: Pick<Agent, "tools">, step: ActionRecipeStep): string {
  const resolved = step.tool ? resolveRecipeTool(agent, step.tool) : null;
  const label = resolved?.instance?.name ?? step.tool;
  if (label && step.command) return `${label}.${step.command}`;
  return label || step.command || "шаг";
}

/** @deprecated pass agent instead of enabledToolIds Set */
export function getRecipeStepStatusLegacy(
  _agentSlug: string,
  step: ActionRecipeStep,
  enabledInstanceIds: Set<string>,
): RecipeStepStatus {
  if (!step.tool) return "unknown";
  if (!enabledInstanceIds.has(step.tool)) {
    const def = getToolDefinition(step.tool);
    if (def && enabledInstanceIds.size) return "disabled";
    if (!def) return "unknown";
    return "disabled";
  }
  const def = getToolDefinition(step.tool);
  if (!def) return "unknown";
  if (step.command && !def.commands.some((command) => command.id === step.command)) {
    return "unknown";
  }
  return "ok";
}
