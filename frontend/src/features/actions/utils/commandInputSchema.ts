import type { ToolFieldDef } from "@/features/tools/types/tool";
import { getToolDefinition } from "@/features/tools/registry/builtinTools";

export function getCommandInputFields(toolTypeId: string, commandId: string): ToolFieldDef[] {
  const tool = getToolDefinition(toolTypeId);
  const command = tool?.commands.find((item) => item.id === commandId);
  return command?.inputSchema ?? [];
}

export function getCommandOutputFields(toolTypeId: string, commandId: string): ToolFieldDef[] {
  const tool = getToolDefinition(toolTypeId);
  const command = tool?.commands.find((item) => item.id === commandId);
  return command?.outputSchema ?? [];
}
