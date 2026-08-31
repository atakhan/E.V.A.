export interface WorkspaceSection {
  id: string;
  slug: string;
  title: string;
  description: string;
}

/** Constructor IA aligned with architecture v1: Agent → Skills / Actions / Tools. */
export const workspaceSections: WorkspaceSection[] = [
  {
    id: "overview",
    slug: "overview",
    title: "Overview",
    description: "Кто этот агент и какими Skills, Actions и Tools он обладает.",
  },
  {
    id: "skills",
    slug: "skills",
    title: "Skills",
    description: "Процессы агента. Каждый Skill описывается через FSM на холсте.",
  },
  {
    id: "actions",
    slug: "actions",
    title: "Actions",
    description: "Именованные поступки агента, собранные из Tools по рецепту.",
  },
  {
    id: "tools",
    slug: "tools",
    title: "Tools",
    description: "Capabilities агента: LLM, Memory, каналы, внешние системы.",
  },
  {
    id: "logs",
    slug: "logs",
    title: "Logs",
    description: "История вызовов Tools: команды, запросы, ответы и ошибки.",
  },
  {
    id: "runtime",
    slug: "runtime",
    title: "Runtime",
    description: "Операционный кокпит: активные runs, cancel, timeline и simulate.",
  },
];

export const defaultWorkspaceSectionId = "overview";
export const defaultWorkspaceSectionSlug = "overview";

export function findWorkspaceSection(idOrSlug: string): WorkspaceSection | undefined {
  return workspaceSections.find(
    (section) => section.id === idOrSlug || section.slug === idOrSlug,
  );
}

export function workspaceSectionSlugFromId(id: string): string {
  return findWorkspaceSection(id)?.slug ?? defaultWorkspaceSectionSlug;
}
