import { defaultModuleSectionId } from "@/features/workspace/config/modules";

export const RouteNames = {
  applications: "applications",
  applicationModule: "application-module",
  fsmCanvas: "fsm-canvas",
} as const;

export const moduleSlugBySectionId: Record<string, string> = {
  "core.fsm": "fsm",
  "core.tasks": "tasks",
  "core.llm": "llm",
  "core.events": "events",
  "tools-and-actions": "tools-and-actions",
  "memory.memory": "memory",
  "memory.entity-graph": "entity-graph",
  "memory.business-data": "business-data",
  "context-manager": "context-manager",
  reflection: "reflection",
};

export const sectionIdByModuleSlug: Record<string, string> = Object.fromEntries(
  Object.entries(moduleSlugBySectionId).map(([sectionId, slug]) => [slug, sectionId]),
);

export const defaultModuleSlug = moduleSlugBySectionId[defaultModuleSectionId];

export function sectionIdFromSlug(slug: string): string | undefined {
  return sectionIdByModuleSlug[slug];
}

export function moduleSlugFromSectionId(sectionId: string): string {
  return moduleSlugBySectionId[sectionId] ?? defaultModuleSlug;
}

export function applicationsPath(): string {
  return "/applications";
}

export function applicationModulePath(appSlug: string, moduleSlug = defaultModuleSlug): string {
  return `/${appSlug}/modules/${moduleSlug}`;
}

export function applicationModulePathBySection(appSlug: string, sectionId: string): string {
  return applicationModulePath(appSlug, moduleSlugFromSectionId(sectionId));
}

export function fsmCanvasPath(appSlug: string, canvasId: string): string {
  return `/${appSlug}/fsm/canvases/${canvasId}`;
}
