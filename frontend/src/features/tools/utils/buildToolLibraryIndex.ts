import type { Agent } from "@/features/agents/types/agent";
import type { ToolDefinition, ToolInstance } from "@/features/tools/types/tool";
import { builtinTools } from "@/features/tools/registry/builtinTools";

export interface ToolLibraryUsageRow {
  agentId: string;
  agentSlug: string;
  agentName: string;
  instance: ToolInstance;
}

export interface ToolLibraryTypeEntry {
  definition: ToolDefinition;
  instances: ToolLibraryUsageRow[];
  agentCount: number;
  enabledCount: number;
}

export interface ToolLibraryIndex {
  types: ToolLibraryTypeEntry[];
  totalInstances: number;
  orphanInstances: ToolLibraryUsageRow[];
}

function compareUsageRows(a: ToolLibraryUsageRow, b: ToolLibraryUsageRow): number {
  const byAgent = a.agentName.localeCompare(b.agentName, "ru");
  if (byAgent !== 0) return byAgent;
  return a.instance.name.localeCompare(b.instance.name, "ru");
}

function compareTypeEntries(a: ToolLibraryTypeEntry, b: ToolLibraryTypeEntry): number {
  const aCount = a.instances.length;
  const bCount = b.instances.length;
  if (aCount > 0 && bCount === 0) return -1;
  if (aCount === 0 && bCount > 0) return 1;
  if (aCount !== bCount) return bCount - aCount;
  return a.definition.name.localeCompare(b.definition.name, "ru");
}

export function buildToolLibraryIndex(
  agents: Agent[],
  catalog: ToolDefinition[] = builtinTools,
): ToolLibraryIndex {
  const catalogIds = new Set(catalog.map((item) => item.id));
  const rowsByType = new Map<string, ToolLibraryUsageRow[]>();
  const orphanInstances: ToolLibraryUsageRow[] = [];

  for (const agent of agents) {
    for (const instance of agent.tools) {
      const row: ToolLibraryUsageRow = {
        agentId: agent.id,
        agentSlug: agent.slug,
        agentName: agent.name,
        instance,
      };

      if (!catalogIds.has(instance.toolId)) {
        orphanInstances.push(row);
        continue;
      }

      const bucket = rowsByType.get(instance.toolId) ?? [];
      bucket.push(row);
      rowsByType.set(instance.toolId, bucket);
    }
  }

  orphanInstances.sort(compareUsageRows);

  const types: ToolLibraryTypeEntry[] = catalog.map((definition) => {
    const instances = (rowsByType.get(definition.id) ?? []).slice().sort(compareUsageRows);
    const agentSlugs = new Set(instances.map((row) => row.agentSlug));
    return {
      definition,
      instances,
      agentCount: agentSlugs.size,
      enabledCount: instances.filter((row) => row.instance.enabled).length,
    };
  });

  types.sort(compareTypeEntries);

  const totalInstances =
    types.reduce((sum, entry) => sum + entry.instances.length, 0) + orphanInstances.length;

  return { types, totalInstances, orphanInstances };
}
