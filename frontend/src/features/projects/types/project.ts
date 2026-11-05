export interface ProjectAgent {
  agentSlug: string;
  /** Library agent this desk copy was forked from. */
  originSlug?: string;
  x: number;
  y: number;
}

export interface Project {
  id: string;
  slug: string;
  name: string;
  description: string;
  agents: ProjectAgent[];
  /** System agent of this project. Hidden from the library. */
  runtimeAgentSlug?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectInput {
  name: string;
  slug: string;
  description: string;
}
