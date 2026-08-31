import { computed } from "vue";
import { agents } from "@/features/agents/services/agentsStorage";
import { useTools } from "@/features/tools/composables/useTools";
import {
  buildToolLibraryIndex,
  type ToolLibraryIndex,
  type ToolLibraryTypeEntry,
  type ToolLibraryUsageRow,
} from "@/features/tools/utils/buildToolLibraryIndex";

function matchesQuery(text: string, query: string): boolean {
  return text.toLowerCase().includes(query);
}

function rowMatchesQuery(row: ToolLibraryUsageRow, query: string): boolean {
  return (
    matchesQuery(row.agentName, query) ||
    matchesQuery(row.agentSlug, query) ||
    matchesQuery(row.instance.name, query) ||
    matchesQuery(row.instance.id, query)
  );
}

function typeEntryMatchesQuery(entry: ToolLibraryTypeEntry, query: string): boolean {
  if (
    matchesQuery(entry.definition.name, query) ||
    matchesQuery(entry.definition.id, query) ||
    matchesQuery(entry.definition.description, query)
  ) {
    return true;
  }
  return entry.instances.some((row) => rowMatchesQuery(row, query));
}

export function filterToolLibraryIndex(index: ToolLibraryIndex, rawQuery: string): ToolLibraryIndex {
  const query = rawQuery.trim().toLowerCase();
  if (!query) return index;

  const types = index.types
    .filter((entry) => typeEntryMatchesQuery(entry, query))
    .map((entry) => {
      const typeMatched =
        matchesQuery(entry.definition.name, query) ||
        matchesQuery(entry.definition.id, query) ||
        matchesQuery(entry.definition.description, query);
      const instances = typeMatched
        ? entry.instances
        : entry.instances.filter((row) => rowMatchesQuery(row, query));
      const agentSlugs = new Set(instances.map((row) => row.agentSlug));
      return {
        ...entry,
        instances,
        agentCount: agentSlugs.size,
        enabledCount: instances.filter((row) => row.instance.enabled).length,
      };
    });

  const orphanInstances = index.orphanInstances.filter((row) => rowMatchesQuery(row, query));
  const totalInstances =
    types.reduce((sum, entry) => sum + entry.instances.length, 0) + orphanInstances.length;

  return { types, totalInstances, orphanInstances };
}

export function useToolLibrary() {
  const { catalog } = useTools();

  const index = computed(() => buildToolLibraryIndex(agents.value, catalog));

  const agentCount = computed(() => agents.value.length);

  const uniqueAgentSlugsWithInstances = computed(() => {
    const slugs = new Set<string>();
    for (const entry of index.value.types) {
      for (const row of entry.instances) {
        slugs.add(row.agentSlug);
      }
    }
    for (const row of index.value.orphanInstances) {
      slugs.add(row.agentSlug);
    }
    return slugs.size;
  });

  return {
    agents,
    catalog,
    index,
    agentCount,
    uniqueAgentSlugsWithInstances,
    filterToolLibraryIndex,
  };
}
