import type { Project, ProjectAgent, ProjectInput } from "@/features/projects/types/project";

import { apiRequest } from "@/shared/api/http";

export function fetchProjects(): Promise<Project[]> {
  return apiRequest("/api/projects");
}

export function fetchProject(slug: string): Promise<Project> {
  return apiRequest(`/api/projects/${encodeURIComponent(slug)}`);
}

export function createProject(input: ProjectInput): Promise<Project> {
  return apiRequest("/api/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateProject(
  slug: string,
  patch: { name?: string; description?: string; agents?: ProjectAgent[] },
): Promise<Project> {
  return apiRequest(`/api/projects/${encodeURIComponent(slug)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteProject(slug: string): Promise<void> {
  return apiRequest(`/api/projects/${encodeURIComponent(slug)}`, { method: "DELETE" });
}
