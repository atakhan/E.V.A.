import { ref } from "vue";
import {
  createProject as createProjectRequest,
  deleteProject as deleteProjectRequest,
  fetchProject,
  fetchProjects,
  updateProject as updateProjectRequest,
} from "@/features/projects/services/projectsApi";
import type { Project, ProjectAgent, ProjectInput } from "@/features/projects/types/project";
import { normalizeAgentSlug, suggestUniqueAgentSlug, validateAgentSlug } from "@/shared/utils/agentSlug";

const projects = ref<Project[]>([]);
const loaded = ref(false);

export function useProjects() {
  async function refresh(): Promise<void> {
    projects.value = await fetchProjects();
    loaded.value = true;
  }

  async function ensureLoaded(): Promise<void> {
    if (!loaded.value) {
      await refresh();
    }
  }

  function isSlugAvailable(slug: string, except?: string): boolean {
    return !projects.value.some((project) => project.slug === slug && project.slug !== except);
  }

  async function createProject(input: ProjectInput): Promise<{ ok: true; project: Project } | { ok: false; error: string }> {
    const name = input.name.trim();
    if (!name) return { ok: false, error: "Укажите название проекта" };
    await ensureLoaded();
    const slugError = validateAgentSlug(input.slug, (candidate) => isSlugAvailable(candidate));
    if (slugError) return { ok: false, error: slugError.replace("агента", "проекта").replace("агент", "проект") };
    try {
      const project = await createProjectRequest({
        name,
        slug: normalizeAgentSlug(input.slug),
        description: input.description.trim(),
      });
      projects.value = [project, ...projects.value.filter((item) => item.id !== project.id)];
      return { ok: true, project };
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : "Не удалось создать проект" };
    }
  }

  async function saveAgents(slug: string, agents: ProjectAgent[]): Promise<Project> {
    const project = await updateProjectRequest(slug, { agents });
    projects.value = projects.value.map((item) => (item.slug === slug ? project : item));
    return project;
  }

  async function saveDetails(slug: string, patch: { name: string; description: string }): Promise<Project> {
    const project = await updateProjectRequest(slug, patch);
    projects.value = projects.value.map((item) => (item.slug === slug ? project : item));
    return project;
  }

  async function removeProject(slug: string): Promise<void> {
    await deleteProjectRequest(slug);
    projects.value = projects.value.filter((item) => item.slug !== slug);
  }

  function suggestSlug(base: string): string {
    return suggestUniqueAgentSlug(base, (candidate) => isSlugAvailable(candidate));
  }

  return {
    projects,
    refresh,
    fetchProject,
    createProject,
    saveAgents,
    saveDetails,
    removeProject,
    suggestSlug,
  };
}
