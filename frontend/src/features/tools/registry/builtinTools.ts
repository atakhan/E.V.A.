import type { ToolDefinition } from "@/features/tools/types/tool";
import {
  getToolCatalog,
  getToolCommandIdsFromCatalog,
  getToolDefinitionFromCatalog,
  isToolCatalogLoaded,
  loadToolCatalog,
} from "@/features/tools/services/toolCatalogStore";

export { loadToolCatalog, isToolCatalogLoaded };

export const builtinTools: ToolDefinition[] = [];

export function getToolDefinition(toolId: string): ToolDefinition | undefined {
  const live = getToolDefinitionFromCatalog(toolId);
  if (live) return live;
  return builtinTools.find((tool) => tool.id === toolId);
}

export function getToolCommandIds(toolId: string): string[] {
  const ids = getToolCommandIdsFromCatalog(toolId);
  if (ids.length) return ids;
  return getToolDefinition(toolId)?.commands.map((command) => command.id) ?? [];
}

export function getBuiltinTools(): ToolDefinition[] {
  const live = getToolCatalog();
  return live.length ? live : builtinTools;
}

export function formatToolCommand(toolId: string, commandId: string): string {
  if (!toolId) return commandId || "(пусто)";
  if (!commandId) return toolId;
  return `${toolId}.${commandId}`;
}
