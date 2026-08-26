import type {
  NavigationGuardNext,
  RouteLocationGeneric,
  RouteLocationNormalized,
} from "vue-router";
import {
  getAgentById,
  getAgentBySlug,
} from "@/features/agents/services/agentsStorage";
import { findWorkspaceSection } from "@/features/workspace/config/nav";
import {
  agentHomePath,
  agentSectionPath,
  agentSkillsPath,
  legacyModuleSlugToSection,
  RouteNames,
  skillPath,
} from "@/router/paths";

const workspaceRouteNames = new Set<string>([
  RouteNames.agentOverview,
  RouteNames.agentSkills,
  RouteNames.agentActions,
  RouteNames.agentTools,
  RouteNames.skillCanvas,
]);

export function agentRouteGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
) {
  if (!to.name || !workspaceRouteNames.has(String(to.name))) {
    next();
    return;
  }

  const agentSlug = String(to.params.agentSlug);
  const agent = getAgentBySlug(agentSlug);
  if (!agent) {
    next({ name: RouteNames.agents });
    return;
  }

  if (to.name === RouteNames.skillCanvas) {
    const skillId = String(to.params.skillId);
    const skill = agent.skills.find((item) => item.id === skillId);
    if (!skill) {
      next(agentSkillsPath(agent.slug));
      return;
    }
  }

  next();
}

export function legacyAgentModuleRedirect(to: RouteLocationGeneric): string {
  const legacyAgentId = String(to.params.legacyAgentId);
  const agent = getAgentById(legacyAgentId) ?? getAgentBySlug(legacyAgentId);
  if (!agent) return "/agents";

  const section = legacyModuleSlugToSection(String(to.params.moduleSlug));
  return agentSectionPath(agent.slug, section);
}

export function legacyAgentSlugModuleRedirect(to: RouteLocationGeneric): string {
  const agentSlug = String(to.params.agentSlug);
  const agent = getAgentBySlug(agentSlug);
  if (!agent) return "/agents";

  const section = legacyModuleSlugToSection(String(to.params.moduleSlug));
  return agentSectionPath(agent.slug, section);
}

export function legacyFsmCanvasRedirect(to: RouteLocationGeneric): string {
  const legacyAgentId = String(to.params.legacyAgentId ?? to.params.agentSlug);
  const agent = getAgentById(legacyAgentId) ?? getAgentBySlug(legacyAgentId);
  if (!agent) return "/agents";

  const skillId = String(to.params.canvasId ?? to.params.skillId);
  if (agent.skills.some((skill) => skill.id === skillId)) {
    return skillPath(agent.slug, skillId);
  }
  return agentSkillsPath(agent.slug);
}

export function legacyAgentRootRedirect(to: RouteLocationGeneric): string {
  const agentSlug = String(to.params.agentSlug);
  if (findWorkspaceSection(agentSlug)) {
    // reserved — should not happen due to reserved slugs
    return "/agents";
  }
  return agentHomePath(agentSlug);
}
