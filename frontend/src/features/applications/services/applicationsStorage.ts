import { ref, watch } from "vue";
import type { Application } from "@/features/applications/types/application";
import type { CanvasDocument } from "@/features/modules/fsm/types/canvas";
import {
  createEmptyApplicationModules,
  getLeafModuleSectionIds,
} from "@/features/workspace/config/modules";
import { FSM_MODULE_ID } from "@/features/modules/fsm/types/fsmModule";
import { createId } from "@/shared/utils/id";
import { normalizeAppSlug, suggestUniqueAppSlug } from "@/shared/utils/appSlug";

const STORAGE_KEY = "eva.applications.v2";
const LEGACY_STORAGE_KEY = "eva.applications.v1";
const LEGACY_CANVASES_KEY = "eva.canvases.v1";

export const applications = ref<Application[]>(loadApplications());

watch(
  applications,
  (value) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  },
  { deep: true },
);

function normalizeApplications(rawApps: Application[]): Application[] {
  const usedSlugs = new Set<string>();

  return rawApps.map((app) => {
    const name = app.name?.trim() || "Приложение";
    let slug = app.slug ? normalizeAppSlug(app.slug) : "";

    if (!slug || usedSlugs.has(slug)) {
      slug = suggestUniqueAppSlug(name, (candidate) => !usedSlugs.has(candidate));
    }

    usedSlugs.add(slug);

    return {
      ...app,
      name,
      slug,
      description: app.description ?? "",
      modules: normalizeModules(app.modules),
    };
  });
}

function normalizeModules(modules: Record<string, unknown> | undefined): Record<string, unknown> {
  const next = createEmptyApplicationModules();
  if (!modules) return next;

  for (const sectionId of getLeafModuleSectionIds()) {
    if (modules[sectionId] !== undefined) {
      next[sectionId] = modules[sectionId];
    }
  }

  return next;
}

function loadApplications(): Application[] {
  migrateLegacyStorage();

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Application[];
    return Array.isArray(parsed) ? normalizeApplications(parsed) : [];
  } catch {
    return [];
  }
}

function migrateLegacyStorage() {
  if (localStorage.getItem(STORAGE_KEY)) return;

  const legacyAppsRaw = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (legacyAppsRaw) {
    try {
      const legacyApps = JSON.parse(legacyAppsRaw) as Application[];
      if (Array.isArray(legacyApps) && legacyApps.length > 0) {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify(normalizeApplications(legacyApps)),
        );
        return;
      }
    } catch {
      // fall through
    }
  }

  migrateLegacyCanvases();
}

function migrateLegacyCanvases() {
  try {
    const raw = localStorage.getItem(LEGACY_CANVASES_KEY);
    if (!raw) return;

    const canvases = JSON.parse(raw) as CanvasDocument[];
    if (!Array.isArray(canvases) || canvases.length === 0) return;

    const now = new Date().toISOString();
    const modules = createEmptyApplicationModules();
    modules[FSM_MODULE_ID] = { canvases };

    const app: Application = {
      id: createId(),
      slug: suggestUniqueAppSlug("app-1", () => true),
      name: "Приложение 1",
      description: "",
      createdAt: now,
      updatedAt: now,
      modules,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify([app]));
  } catch {
    // ignore broken legacy data
  }
}

export function touchApplication(app: Application): Application {
  return { ...app, updatedAt: new Date().toISOString() };
}

export function replaceApplication(next: Application) {
  const index = applications.value.findIndex((app) => app.id === next.id);
  if (index === -1) return;

  applications.value = [
    ...applications.value.slice(0, index),
    next,
    ...applications.value.slice(index + 1),
  ];
}

export function getApplicationById(id: string): Application | undefined {
  return applications.value.find((app) => app.id === id);
}

export function getApplicationBySlug(slug: string): Application | undefined {
  const normalized = normalizeAppSlug(slug);
  return applications.value.find((app) => app.slug === normalized);
}

export function isSlugAvailable(slug: string, excludeAppId?: string): boolean {
  const normalized = normalizeAppSlug(slug);
  return !applications.value.some(
    (app) => app.slug === normalized && app.id !== excludeAppId,
  );
}
