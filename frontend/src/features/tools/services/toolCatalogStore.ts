import type { ToolDefinition } from "@/features/tools/types/tool";

const STORAGE_KEY = "eva.toolCatalog.v1";

let catalog: ToolDefinition[] = [];
let loaded = false;
let loading: Promise<void> | null = null;

function readCache(): ToolDefinition[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ToolDefinition[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeCache(value: ToolDefinition[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // ignore quota errors
  }
}

export function getToolCatalog(): ToolDefinition[] {
  return catalog;
}

export function isToolCatalogLoaded(): boolean {
  return loaded;
}

export function getToolDefinitionFromCatalog(toolId: string): ToolDefinition | undefined {
  return catalog.find((tool) => tool.id === toolId);
}

export function getToolCommandIdsFromCatalog(toolId: string): string[] {
  return getToolDefinitionFromCatalog(toolId)?.commands.map((command) => command.id) ?? [];
}

export async function loadToolCatalog(): Promise<void> {
  if (loading) return loading;
  loading = (async () => {
    const cached = readCache();
    if (cached.length) catalog = cached;
    try {
      const response = await fetch("/api/tools/catalog");
      if (response.ok) {
        catalog = (await response.json()) as ToolDefinition[];
        writeCache(catalog);
      }
    } catch {
      if (!catalog.length) catalog = cached;
    } finally {
      loaded = true;
      loading = null;
    }
  })();
  return loading;
}

export function setToolCatalogForTests(value: ToolDefinition[]) {
  catalog = value;
  loaded = true;
}
