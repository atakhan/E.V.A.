export interface ProjectQuestion {
  id: string;
  text: string;
}

const STORAGE_KEY = "eva.projectQuestions.v1";

function readAll(): Record<string, ProjectQuestion[]> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Record<string, ProjectQuestion[]>;
  } catch {
    return {};
  }
}

export function readProjectQuestions(slug: string): ProjectQuestion[] {
  const items = readAll()[slug];
  if (!Array.isArray(items)) return [];
  return items.filter(
    (item): item is ProjectQuestion =>
      Boolean(item) && typeof item.id === "string" && typeof item.text === "string",
  );
}

export function writeProjectQuestions(slug: string, items: ProjectQuestion[]): void {
  const all = readAll();
  all[slug] = items;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}
