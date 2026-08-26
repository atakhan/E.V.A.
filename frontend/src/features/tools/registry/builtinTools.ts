import type { ToolDefinition } from "@/features/tools/types/tool";

/** Built-in constructor catalog — Phase 3 static registry. */
export const builtinTools: ToolDefinition[] = [
  {
    id: "llm",
    name: "LLM",
    description: "Языковая модель: текст и структурированный вывод.",
    commands: [
      { id: "run", description: "Свободный текстовый ответ" },
      { id: "run_structured", description: "Ответ по JSON-схеме" },
    ],
    events: [],
    states: [],
  },
  {
    id: "memory",
    name: "Memory",
    description: "Поиск по опыту и заметкам агента.",
    commands: [{ id: "search", description: "Семантический / ключевой поиск" }],
    events: [],
    states: [],
  },
  {
    id: "context",
    name: "Context",
    description: "Сборка порции мира на один шаг.",
    commands: [{ id: "build", description: "Собрать контекст по recipe" }],
    events: [],
    states: [],
  },
  {
    id: "telegram",
    name: "Telegram",
    description: "Канал сообщений с людьми.",
    commands: [{ id: "send_message", description: "Отправить сообщение" }],
    events: [
      { id: "channel.message.received", description: "Входящее сообщение" },
    ],
    states: ["connected", "disconnected"],
  },
  {
    id: "crm",
    name: "CRM",
    description: "Заявки и сущности в рабочей системе.",
    commands: [
      { id: "update", description: "Обновить сущность" },
      { id: "get", description: "Прочитать сущность" },
    ],
    events: [
      { id: "crm.request.created", description: "Создана заявка" },
      { id: "crm.request.updated", description: "Обновлена заявка" },
    ],
    states: [],
  },
  {
    id: "catalog",
    name: "Catalog",
    description: "Справочник ТМЦ и альтернатив.",
    commands: [
      { id: "search_tmc", description: "Поиск позиций ТМЦ" },
      { id: "search", description: "Общий поиск по каталогу" },
    ],
    events: [],
    states: [],
  },
  {
    id: "web_search",
    name: "Web Search",
    description: "Поиск во внешнем вебе.",
    commands: [{ id: "search", description: "Веб-поиск" }],
    events: [],
    states: [],
  },
  {
    id: "files",
    name: "Files",
    description: "Чтение и запись файлов.",
    commands: [
      { id: "read", description: "Прочитать файл" },
      { id: "write", description: "Записать файл" },
    ],
    events: [],
    states: [],
  },
  {
    id: "saby",
    name: "Saby",
    description: "Интеграция со СБИС / документооборотом.",
    commands: [
      { id: "send_document", description: "Отправить документ" },
      { id: "get_status", description: "Статус документа" },
    ],
    events: [{ id: "saby.document.updated", description: "Обновлён статус документа" }],
    states: [],
  },
];

export function getToolDefinition(toolId: string): ToolDefinition | undefined {
  return builtinTools.find((tool) => tool.id === toolId);
}

export function getToolCommandIds(toolId: string): string[] {
  return getToolDefinition(toolId)?.commands.map((command) => command.id) ?? [];
}

export function formatToolCommand(toolId: string, commandId: string): string {
  if (!toolId) return commandId || "(пусто)";
  if (!commandId) return toolId;
  return `${toolId}.${commandId}`;
}
