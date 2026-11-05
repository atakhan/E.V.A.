import type { Project, ProjectAgent, ProjectInput } from "@/features/projects/types/project";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function fetchProjects(): Promise<Project[]> {
  return request("/api/projects");
}

export function fetchProject(slug: string): Promise<Project> {
  return request(`/api/projects/${encodeURIComponent(slug)}`);
}

export function createProject(input: ProjectInput): Promise<Project> {
  return request("/api/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateProject(
  slug: string,
  patch: { name?: string; description?: string; agents?: ProjectAgent[] },
): Promise<Project> {
  return request(`/api/projects/${encodeURIComponent(slug)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteProject(slug: string): Promise<void> {
  return request(`/api/projects/${encodeURIComponent(slug)}`, { method: "DELETE" });
}
