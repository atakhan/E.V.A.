import { defaultWorkspaceSectionSlug } from "@/features/workspace/config/nav";

export const RouteNames = {
  agents: "agents",
  toolsLibrary: "tools-library",
  globalRuntime: "global-runtime",
  agentWorkspace: "agent-workspace",
  agentOverview: "agent-overview",
  agentSkills: "agent-skills",
  agentActions: "agent-actions",
  agentTools: "agent-tools",
  agentToolInstance: "agent-tool-instance",
  agentLogs: "agent-logs",
  agentRuntime: "agent-runtime",
  agentRuntimeSimulate: "agent-runtime-simulate",
  skillRunDetail: "skill-run-detail",
  agentRun: "agent-run",
  skillCanvas: "skill-canvas",
} as const;

export function agentsPath(): string {
  return "/agents";
}

export function globalRuntimePath(): string {
  return "/runtime";
}

export function toolsLibraryPath(): string {
  return "/tools";
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

export function agentActionPath(
  agentSlug: string,
  actionId?: string,
  createId?: string,
): string {
  const base = agentActionsPath(agentSlug);
  const params = new URLSearchParams();
  if (actionId) params.set("action", actionId);
  if (createId) params.set("create", createId);
  const suffix = params.toString();
  return suffix ? `${base}?${suffix}` : base;
}

export function agentToolsPath(agentSlug: string): string {
  return agentSectionPath(agentSlug, "tools");
}

export function agentToolInstancePath(agentSlug: string, instanceId: string): string {
  return `${agentToolsPath(agentSlug)}/${encodeURIComponent(instanceId)}`;
}

export function agentLogsPath(
  agentSlug: string,
  query?: Record<string, string | undefined>,
): string {
  const base = agentSectionPath(agentSlug, "logs");
  if (!query) return base;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const suffix = params.toString();
  return suffix ? `${base}?${suffix}` : base;
}

export function agentRuntimePath(agentSlug: string): string {
  return agentSectionPath(agentSlug, "runtime");
}

export function agentRuntimeSimulatePath(agentSlug: string): string {
  return `${agentRuntimePath(agentSlug)}/simulate`;
}

export function skillRunDetailPath(agentSlug: string, runId: string): string {
  return `${agentRuntimePath(agentSlug)}/runs/${encodeURIComponent(runId)}`;
}

/** @deprecated Use agentRuntimeSimulatePath */
export function agentRunPath(agentSlug: string): string {
  return agentRuntimeSimulatePath(agentSlug);
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
  if (moduleSlug === "run") return "runtime/simulate";
  if (
    moduleSlug === "overview" ||
    moduleSlug === "skills" ||
    moduleSlug === "actions" ||
    moduleSlug === "tools" ||
    moduleSlug === "logs" ||
    moduleSlug === "runtime"
  ) {
    return moduleSlug;
  }
  return defaultWorkspaceSectionSlug;
}
