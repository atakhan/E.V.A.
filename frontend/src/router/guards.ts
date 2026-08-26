import type {
  NavigationGuardNext,
  RouteLocationGeneric,
  RouteLocationNormalized,
} from "vue-router";
import {
  getApplicationById,
  getApplicationBySlug,
} from "@/features/applications/services/applicationsStorage";
import { getFsmModuleData } from "@/features/modules/fsm/types/fsmModule";
import {
  applicationModulePath,
  defaultModuleSlug,
  RouteNames,
  sectionIdFromSlug,
} from "@/router/paths";

export function applicationRouteGuard(
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext,
) {
  if (
    to.name !== RouteNames.applicationModule &&
    to.name !== RouteNames.fsmCanvas
  ) {
    next();
    return;
  }

  const appSlug = String(to.params.appSlug);
  const app = getApplicationBySlug(appSlug);
  if (!app) {
    next({ name: RouteNames.applications });
    return;
  }

  if (to.name === RouteNames.applicationModule) {
    const moduleSlug = String(to.params.moduleSlug);
    if (!sectionIdFromSlug(moduleSlug)) {
      next(applicationModulePath(app.slug, defaultModuleSlug));
      return;
    }
  }

  if (to.name === RouteNames.fsmCanvas) {
    const canvasId = String(to.params.canvasId);
    const canvas = getFsmModuleData(app.modules).canvases.find(
      (item) => item.id === canvasId,
    );

    if (!canvas) {
      next(applicationModulePath(app.slug, defaultModuleSlug));
      return;
    }
  }

  next();
}

export function legacyApplicationRedirect(to: RouteLocationGeneric): string {
  const legacyAppId = String(to.params.legacyAppId);
  const app =
    getApplicationById(legacyAppId) ?? getApplicationBySlug(legacyAppId);

  if (!app) return "/applications";

  const moduleSlug = sectionIdFromSlug(String(to.params.moduleSlug))
    ? String(to.params.moduleSlug)
    : defaultModuleSlug;

  return applicationModulePath(app.slug, moduleSlug);
}

export function legacyFsmCanvasRedirect(to: RouteLocationGeneric): string {
  const legacyAppId = String(to.params.legacyAppId);
  const app = getApplicationById(legacyAppId);
  if (!app) return "/applications";
  return `/${app.slug}/fsm/canvases/${String(to.params.canvasId)}`;
}
