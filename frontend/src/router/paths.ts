import { defaultWorkspaceSectionSlug } from "@/features/workspace/config/nav";

export const RouteNames = {
  agents: "agents",
  agentWorkspace: "agent-workspace",
  agentOverview: "agent-overview",
  agentSkills: "agent-skills",
  agentActions: "agent-actions",
  agentTools: "agent-tools",
  agentRun: "agent-run",
  skillCanvas: "skill-canvas",
} as const;

export function agentsPath(): string {
  return "/agents";
}

export function agentOverviewPath(agentSlug: string): string {
  return `/${agentSlug}/overview`;
}

export function agentSectionPath(agentSlug: string, sectionSlug: string): string {
  return `/${agentSlug}/${sectionSlug}`;
}

export function agentSkillsPath(agentSlug: string): string {
  return agentSectionPath(agentSlug, "skills");
}

export function agentActionsPath(agentSlug: string): string {
  return agentSectionPath(agentSlug, "actions");
}

export function agentToolsPath(agentSlug: string): string {
  return agentSectionPath(agentSlug, "tools");
}

export function agentRunPath(agentSlug: string): string {
  return agentSectionPath(agentSlug, "run");
}

export function skillPath(agentSlug: string, skillId: string): string {
  return `/${agentSlug}/skills/${skillId}`;
}

/** Default landing inside an agent workspace. */
export function agentHomePath(agentSlug: string): string {
  return agentSectionPath(agentSlug, defaultWorkspaceSectionSlug);
}

/** Map legacy module slugs to constructor sections. */
export function legacyModuleSlugToSection(moduleSlug: string): string {
  if (moduleSlug === "fsm") return "skills";
  if (moduleSlug === "tools-and-actions") return "tools";
  if (
    moduleSlug === "overview" ||
    moduleSlug === "skills" ||
    moduleSlug === "actions" ||
    moduleSlug === "tools" ||
    moduleSlug === "run"
  ) {
    return moduleSlug;
  }
  return defaultWorkspaceSectionSlug;
}
