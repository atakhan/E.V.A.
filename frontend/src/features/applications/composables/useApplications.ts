import type {
  Application,
  ApplicationInput,
  ApplicationMutationResult,
} from "@/features/applications/types/application";
import {
  applications,
  getApplicationById,
  getApplicationBySlug,
  isSlugAvailable,
  replaceApplication,
  touchApplication,
} from "@/features/applications/services/applicationsStorage";
import { createEmptyApplicationModules } from "@/features/workspace/config/modules";
import { createId } from "@/shared/utils/id";
import {
  normalizeAppSlug,
  suggestUniqueAppSlug,
  validateAppSlug,
} from "@/shared/utils/appSlug";

function createApplicationDocument(input: ApplicationInput): Application {
  const now = new Date().toISOString();
  return {
    id: createId(),
    slug: normalizeAppSlug(input.slug),
    name: input.name.trim(),
    description: input.description?.trim() ?? "",
    createdAt: now,
    updatedAt: now,
    modules: createEmptyApplicationModules(),
  };
}

export function useApplications() {
  function createApplication(input: ApplicationInput): ApplicationMutationResult {
    const name = input.name.trim();
    if (!name) {
      return { ok: false, error: "Укажите название приложения" };
    }

    const slugError = validateAppSlug(input.slug, (candidate) => isSlugAvailable(candidate));
    if (slugError) {
      return { ok: false, error: slugError };
    }

    const app = createApplicationDocument(input);
    applications.value = [app, ...applications.value];
    return { ok: true, app };
  }

  function updateApplication(
    id: string,
    patch: Partial<ApplicationInput>,
  ): ApplicationMutationResult {
    const app = getApplicationById(id);
    if (!app) {
      return { ok: false, error: "Приложение не найдено" };
    }

    const name = patch.name?.trim() || app.name;
    const slugCandidate = patch.slug !== undefined ? patch.slug : app.slug;
    const slugError = validateAppSlug(slugCandidate, (candidate) =>
      isSlugAvailable(candidate, id),
    );

    if (slugError) {
      return { ok: false, error: slugError };
    }

    const next = touchApplication({
      ...app,
      name,
      slug: normalizeAppSlug(slugCandidate),
      description: patch.description?.trim() ?? app.description,
    });

    replaceApplication(next);
    return { ok: true, app: next };
  }

  function deleteApplication(id: string) {
    applications.value = applications.value.filter((app) => app.id !== id);
  }

  return {
    applications,
    getApplicationById,
    getApplicationBySlug,
    isSlugAvailable,
    suggestUniqueAppSlug: (base: string, excludeAppId?: string) =>
      suggestUniqueAppSlug(base, (candidate) => isSlugAvailable(candidate, excludeAppId)),
    createApplication,
    updateApplication,
    deleteApplication,
  };
}
