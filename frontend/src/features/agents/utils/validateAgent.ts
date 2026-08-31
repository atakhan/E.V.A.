import type { Agent } from "@/features/agents/types/agent";
import { isValidActionVersion } from "@/features/actions/types/normalize";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import { resolveRecipeTool } from "@/features/tools/utils/resolveToolInstance";
import { validateSkill } from "@/features/skills/utils/validateSkill";
import {
  agentActionsPath,
  agentSkillsPath,
  agentToolsPath,
  skillPath,
} from "@/router/paths";

export type AgentIssueSeverity = "error" | "warning" | "info";

export type SkillIssueLocator =
  | { kind: "skill" }
  | { kind: "state"; stateId: string }
  | { kind: "transition"; stateId: string; transitionId: string }
  | { kind: "param"; index: number };

export interface AgentIssue {
  id: string;
  severity: AgentIssueSeverity;
  code: string;
  message: string;
  href?: string;
  locator?: SkillIssueLocator;
  actionId?: string;
}

export interface AgentValidationReport {
  issues: AgentIssue[];
  errors: number;
  warnings: number;
  infos: number;
}

function collectReferencedActionIds(agent: Agent): Set<string> {
  const ids = new Set<string>();
  for (const skill of agent.skills) {
    for (const state of skill.states) {
      for (const actionId of state.onEnter) ids.add(actionId);
      for (const transition of state.transitions) {
        for (const actionId of transition.actions) ids.add(actionId);
      }
    }
  }
  return ids;
}

export function validateAgent(agent: Agent): AgentValidationReport {
  const issues: AgentIssue[] = [];
  const actionIds = new Set(agent.actions.map((action) => action.id));
  const enabledInstanceIds = new Set(
    agent.tools.filter((tool) => tool.enabled).map((tool) => tool.id),
  );
  const referencedActions = collectReferencedActionIds(agent);

  if (agent.skills.length === 0) {
    issues.push({
      id: "agent.no-skills",
      severity: "info",
      code: "no_skills",
      message: "У агента пока нет Skills",
      href: agentSkillsPath(agent.slug),
    });
  }

  for (const skill of agent.skills) {
    issues.push(...validateSkill(skill, actionIds, skillPath(agent.slug, skill.id)));
  }

  for (const action of agent.actions) {
    const actionHref = agentActionsPath(agent.slug);

    if (!isValidActionVersion(action.version)) {
      issues.push({
        id: `action.${action.id}.bad-version`,
        severity: "warning",
        code: "invalid_action_version",
        message: `Action «${action.name}»: version «${action.version}» не SemVer (ожидается X.Y.Z)`,
        href: actionHref,
      });
    }

    if (action.policy !== "auto" && action.policy !== "needs_human") {
      issues.push({
        id: `action.${action.id}.bad-policy`,
        severity: "error",
        code: "invalid_action_policy",
        message: `Action «${action.name}»: policy «${action.policy}» недопустим`,
        href: actionHref,
      });
    }

    if (action.recipe.length === 0) {
      issues.push({
        id: `action.${action.id}.empty-recipe`,
        severity: "warning",
        code: "empty_recipe",
        message: `Action «${action.name}» без шагов recipe`,
        href: actionHref,
      });
    }

    const stepIds = new Set<string>();
    for (const step of action.recipe) {
      if (step.id) {
        if (stepIds.has(step.id)) {
          issues.push({
            id: `action.${action.id}.step.${step.id}.duplicate`,
            severity: "error",
            code: "duplicate_step_id",
            message: `Action «${action.name}»: дублирующийся step id «${step.id}»`,
            href: actionHref,
          });
        }
        stepIds.add(step.id);
      }

      const resolved = step.tool ? resolveRecipeTool(agent, step.tool) : null;
      const typeId = resolved?.typeId ?? step.tool;
      const label = step.tool && step.command ? `${step.tool}.${step.command}` : step.tool || step.command || "шаг";
      const def = typeId ? getToolDefinition(typeId) : undefined;

      if (!step.tool || !resolved || resolved.status === "unknown") {
        issues.push({
          id: `action.${action.id}.step.${step.id}.unknown-tool`,
          severity: "error",
          code: "unknown_tool_instance",
          message: `Action «${action.name}»: неизвестный Tool instance в шаге «${label}»`,
          href: actionHref,
        });
        continue;
      }

      if (resolved.status === "ambiguous") {
        issues.push({
          id: `action.${action.id}.step.${step.id}.ambiguous-tool`,
          severity: "error",
          code: "ambiguous_tool_reference",
          message: `Action «${action.name}»: «${step.tool}» неоднозначен — укажите instance id`,
          href: actionHref,
        });
        continue;
      }

      if (resolved.status === "disabled" || !enabledInstanceIds.has(resolved.instanceId)) {
        issues.push({
          id: `action.${action.id}.step.${step.id}.tool-off`,
          severity: "error",
          code: "disabled_tool_instance",
          message: `Action «${action.name}»: instance «${resolved.instanceId}» не подключён`,
          href: agentToolsPath(agent.slug),
        });
      }

      if (!def) {
        issues.push({
          id: `action.${action.id}.step.${step.id}.unknown-type`,
          severity: "error",
          code: "unknown_tool",
          message: `Action «${action.name}»: неизвестный тип Tool «${typeId}»`,
          href: actionHref,
        });
        continue;
      }

      if (step.command && !def.commands.some((command) => command.id === step.command)) {
        issues.push({
          id: `action.${action.id}.step.${step.id}.unknown-command`,
          severity: "error",
          code: "unknown_command",
          message: `Action «${action.name}»: нет команды «${typeId}.${step.command}» в каталоге`,
          href: actionHref,
        });
      }
    }

    if (!referencedActions.has(action.id)) {
      issues.push({
        id: `action.${action.id}.unused`,
        severity: "info",
        code: "unused_action",
        message: `Action «${action.name}» нигде не используется в Skills`,
        href: actionHref,
      });
    }
  }

  if (enabledInstanceIds.size === 0 && agent.actions.some((action) => action.recipe.length > 0)) {
    issues.push({
      id: "agent.no-enabled-tools",
      severity: "warning",
      code: "no_enabled_tools",
      message: "Есть Actions с recipe, но ни один Tool instance не подключён",
      href: agentToolsPath(agent.slug),
    });
  }

  const errors = issues.filter((issue) => issue.severity === "error").length;
  const warnings = issues.filter((issue) => issue.severity === "warning").length;
  const infos = issues.filter((issue) => issue.severity === "info").length;

  return { issues, errors, warnings, infos };
}

export function actionUsageCount(agent: Agent, actionId: string): number {
  let count = 0;
  for (const skill of agent.skills) {
    for (const state of skill.states) {
      count += state.onEnter.filter((id) => id === actionId).length;
      for (const transition of state.transitions) {
        count += transition.actions.filter((id) => id === actionId).length;
      }
    }
  }
  return count;
}
