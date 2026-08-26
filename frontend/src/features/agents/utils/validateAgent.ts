import type { Agent } from "@/features/agents/types/agent";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";
import {
  agentActionsPath,
  agentSkillsPath,
  agentToolsPath,
  skillPath,
} from "@/router/paths";

export type AgentIssueSeverity = "error" | "warning" | "info";

export interface AgentIssue {
  id: string;
  severity: AgentIssueSeverity;
  code: string;
  message: string;
  href?: string;
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
  const enabledTools = new Set(
    agent.tools.filter((tool) => tool.enabled).map((tool) => tool.toolId),
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
    const skillHref = skillPath(agent.slug, skill.id);
    const stateIds = new Set(skill.states.map((state) => state.id));

    if (skill.states.length === 0) {
      issues.push({
        id: `skill.${skill.id}.empty`,
        severity: "warning",
        code: "skill_empty",
        message: `Skill «${skill.name}» без states`,
        href: skillHref,
      });
      continue;
    }

    if (!skill.initial) {
      issues.push({
        id: `skill.${skill.id}.no-initial`,
        severity: "error",
        code: "missing_initial",
        message: `Skill «${skill.name}»: не задан initial state`,
        href: skillHref,
      });
    } else if (!stateIds.has(skill.initial)) {
      issues.push({
        id: `skill.${skill.id}.bad-initial`,
        severity: "error",
        code: "invalid_initial",
        message: `Skill «${skill.name}»: initial «${skill.initial}» отсутствует среди states`,
        href: skillHref,
      });
    }

    for (const state of skill.states) {
      for (const actionId of state.onEnter) {
        if (!actionIds.has(actionId)) {
          issues.push({
            id: `skill.${skill.id}.state.${state.id}.on_enter.${actionId}`,
            severity: "error",
            code: "unknown_action",
            message: `Skill «${skill.name}» / ${state.id}: on_enter ссылается на неизвестный Action «${actionId}»`,
            href: skillHref,
          });
        }
      }

      for (const transition of state.transitions) {
        if (!transition.event.trim()) {
          issues.push({
            id: `skill.${skill.id}.transition.${transition.id}.event`,
            severity: "warning",
            code: "empty_event",
            message: `Skill «${skill.name}» / ${state.id}→${transition.to || "?"}: пустой event`,
            href: skillHref,
          });
        }

        if (!transition.to || !stateIds.has(transition.to)) {
          issues.push({
            id: `skill.${skill.id}.transition.${transition.id}.to`,
            severity: "error",
            code: "invalid_transition_target",
            message: `Skill «${skill.name}» / ${state.id}: переход ведёт в неизвестный state «${transition.to || "—"}»`,
            href: skillHref,
          });
        }

        for (const actionId of transition.actions) {
          if (!actionIds.has(actionId)) {
            issues.push({
              id: `skill.${skill.id}.transition.${transition.id}.action.${actionId}`,
              severity: "error",
              code: "unknown_action",
              message: `Skill «${skill.name}» / ${state.id}: transition ссылается на неизвестный Action «${actionId}»`,
              href: skillHref,
            });
          }
        }
      }
    }
  }

  for (const action of agent.actions) {
    const actionHref = agentActionsPath(agent.slug);

    if (action.recipe.length === 0) {
      issues.push({
        id: `action.${action.id}.empty-recipe`,
        severity: "warning",
        code: "empty_recipe",
        message: `Action «${action.name}» без шагов recipe`,
        href: actionHref,
      });
    }

    for (const step of action.recipe) {
      const label = step.tool && step.command ? `${step.tool}.${step.command}` : step.tool || step.command || "шаг";
      const def = step.tool ? getToolDefinition(step.tool) : undefined;

      if (!step.tool || !def) {
        issues.push({
          id: `action.${action.id}.step.${step.id}.unknown-tool`,
          severity: "error",
          code: "unknown_tool",
          message: `Action «${action.name}»: неизвестный Tool в шаге «${label}»`,
          href: actionHref,
        });
        continue;
      }

      if (!enabledTools.has(step.tool)) {
        issues.push({
          id: `action.${action.id}.step.${step.id}.tool-off`,
          severity: "error",
          code: "disabled_tool",
          message: `Action «${action.name}»: Tool «${step.tool}» не подключён у агента`,
          href: agentToolsPath(agent.slug),
        });
      }

      if (
        step.command &&
        !def.commands.some((command) => command.id === step.command)
      ) {
        issues.push({
          id: `action.${action.id}.step.${step.id}.unknown-command`,
          severity: "error",
          code: "unknown_command",
          message: `Action «${action.name}»: нет команды «${step.tool}.${step.command}» в каталоге`,
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

  if (enabledTools.size === 0 && agent.actions.some((action) => action.recipe.length > 0)) {
    issues.push({
      id: "agent.no-enabled-tools",
      severity: "warning",
      code: "no_enabled_tools",
      message: "Есть Actions с recipe, но ни один Tool не подключён",
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
