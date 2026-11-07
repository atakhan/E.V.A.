import type { ActionDef, ActionPolicy, ActionRecipeStep } from "@/features/actions/types/action";
import { createRecipeStep, isValidActionId, normalizeActionId } from "@/features/actions/types/normalize";

export const SSH_COMMANDS_TOOL_ID = "ssh_commands";
export const SSH_RUN_COMMAND = "run";

export interface SshLibraryCommand {
  id: string;
  name: string;
  description: string;
  shell: string;
  timeoutSec?: number;
}

export interface SshConnectionDraft {
  host: string;
  port: string;
  username: string;
  timeoutSec: string;
  outputLimit: string;
  hostKeyPolicy: "accept-new" | "yes";
}

export interface SshCommandDraft {
  id: string;
  name: string;
  description: string;
  shell: string;
  timeoutSec: string;
}

export function readSshLibrary(config: Record<string, unknown> | undefined): SshLibraryCommand[] {
  const raw = config?.commands;
  if (!Array.isArray(raw)) return [];
  const seen = new Set<string>();
  const items: SshLibraryCommand[] = [];
  for (const entry of raw) {
    if (!entry || typeof entry !== "object") continue;
    const record = entry as Record<string, unknown>;
    const id = typeof record.id === "string" ? record.id.trim() : "";
    const shell = typeof record.shell === "string" ? record.shell : "";
    if (!isValidActionId(id) || !shell.trim() || seen.has(id)) continue;
    seen.add(id);
    const command: SshLibraryCommand = {
      id,
      name: typeof record.name === "string" && record.name.trim() ? record.name.trim() : id,
      description: typeof record.description === "string" ? record.description.trim() : "",
      shell,
    };
    if (typeof record.timeoutSec === "number" && Number.isInteger(record.timeoutSec) && record.timeoutSec > 0) {
      command.timeoutSec = record.timeoutSec;
    }
    items.push(command);
  }
  return items;
}

export function writeSshLibrary(
  config: Record<string, unknown>,
  commands: SshLibraryCommand[],
): Record<string, unknown> {
  return {
    ...config,
    commands: commands.map((command) => {
      const stored: Record<string, unknown> = {
        id: command.id,
        name: command.name,
        description: command.description,
        shell: command.shell,
      };
      if (command.timeoutSec) stored.timeoutSec = command.timeoutSec;
      return stored;
    }),
  };
}

export function parseConnection(config: Record<string, unknown> | undefined): SshConnectionDraft {
  return {
    host: typeof config?.host === "string" ? config.host : "",
    port: config?.port == null || config.port === "" ? "22" : String(config.port),
    username: typeof config?.username === "string" ? config.username : "",
    timeoutSec: config?.timeoutSec == null || config.timeoutSec === "" ? "30" : String(config.timeoutSec),
    outputLimit: config?.outputLimit == null || config.outputLimit === "" ? "8000" : String(config.outputLimit),
    hostKeyPolicy: config?.hostKeyPolicy === "yes" ? "yes" : "accept-new",
  };
}

export function connectionConfigPatch(
  draft: SshConnectionDraft,
): { ok: true; patch: Record<string, unknown> } | { ok: false; error: string } {
  const host = draft.host.trim();
  const username = draft.username.trim();
  if (/\s/.test(host)) return { ok: false, error: "Хост не должен содержать пробелы" };
  if (/\s/.test(username)) return { ok: false, error: "Пользователь не должен содержать пробелы" };
  const port = Number(draft.port);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return { ok: false, error: "Порт — целое число от 1 до 65535" };
  }
  const timeoutSec = Number(draft.timeoutSec);
  if (!Number.isInteger(timeoutSec) || timeoutSec < 1 || timeoutSec > 300) {
    return { ok: false, error: "Таймаут — целое число секунд от 1 до 300" };
  }
  const outputLimit = Number(draft.outputLimit);
  if (!Number.isInteger(outputLimit) || outputLimit < 256 || outputLimit > 100000) {
    return { ok: false, error: "Лимит вывода — целое число от 256 до 100000" };
  }
  return {
    ok: true,
    patch: {
      host,
      port,
      username,
      timeoutSec,
      outputLimit,
      hostKeyPolicy: draft.hostKeyPolicy === "yes" ? "yes" : "accept-new",
    },
  };
}

export function validateCommandDraft(
  draft: SshCommandDraft,
  existingIds: string[],
): string | null {
  if (!draft.name.trim()) return "Укажите название команды";
  const id = normalizeActionId(draft.id || draft.name);
  if (!isValidActionId(id)) return "ID: латиница, цифры и _; начинается с буквы";
  if (existingIds.includes(id)) return "Такая команда уже есть";
  if (!draft.shell.trim()) return "Введите команду, которую нужно выполнить на машине";
  if (draft.timeoutSec.trim()) {
    const timeout = Number(draft.timeoutSec);
    if (!Number.isInteger(timeout) || timeout < 1 || timeout > 300) {
      return "Таймаут команды — целое число секунд от 1 до 300";
    }
  }
  return null;
}

export function commandFromDraft(draft: SshCommandDraft): SshLibraryCommand {
  const command: SshLibraryCommand = {
    id: normalizeActionId(draft.id || draft.name),
    name: draft.name.trim(),
    description: draft.description.trim(),
    shell: draft.shell,
  };
  if (draft.timeoutSec.trim()) command.timeoutSec = Number(draft.timeoutSec);
  return command;
}

export function recipeFromCommandIds(instanceId: string, commandIds: string[]): ActionRecipeStep[] {
  return commandIds.map((commandId, index) =>
    createRecipeStep({
      id: `run_${index + 1}`,
      tool: instanceId,
      command: SSH_RUN_COMMAND,
      input: { command_id: commandId },
    }),
  );
}

export function isSshLibraryAction(action: ActionDef, instanceId: string): boolean {
  if (action.recipe.length === 0) return false;
  return action.recipe.every((step) => {
    const commandId = step.input.command_id;
    return (
      step.tool === instanceId &&
      step.command === SSH_RUN_COMMAND &&
      typeof commandId === "string" &&
      commandId.length > 0
    );
  });
}

export function libraryCommandIds(action: ActionDef): string[] {
  return action.recipe.map((step) => String(step.input.command_id ?? ""));
}

export function actionsUsingCommand(
  actions: ActionDef[],
  instanceId: string,
  commandId: string,
): ActionDef[] {
  return actions.filter((action) =>
    action.recipe.some((step) => step.tool === instanceId && step.input.command_id === commandId),
  );
}

export function validateActionDraft(
  draft: { name: string; id: string; commandIds: string[] },
  existingIds: string[],
): string | null {
  if (!draft.name.trim()) return "Укажите название действия";
  const id = normalizeActionId(draft.id || draft.name);
  if (!isValidActionId(id)) return "ID: латиница, цифры и _; начинается с буквы";
  if (existingIds.includes(id)) return "Такое действие уже есть";
  if (draft.commandIds.length === 0 || draft.commandIds.some((commandId) => !commandId)) {
    return "Выберите хотя бы одну команду";
  }
  return null;
}

export { isValidActionId, normalizeActionId };
export type { ActionPolicy };
