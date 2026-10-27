import type { AgentMemoryEvent, AgentMemoryRun } from "@/features/runtime/types/runtime";

export interface MemoryCardLines {
  historyLine: string;
  stateLine: string;
}

const STATUS_WORD: Record<string, string> = {
  running: "идёт",
  waiting: "ждёт",
  error: "ошибка",
  completed: "завершён",
  cancelled: "отменён",
};

export function runStatusWord(status: string): string {
  return STATUS_WORD[status] ?? status;
}

export function formatMemoryValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value === "" ? "—" : value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

export function describeMemoryCard(
  memory: { events: AgentMemoryEvent[]; runs: AgentMemoryRun[] } | null,
  state: { loading: boolean; failed: boolean },
): MemoryCardLines {
  if (!memory) {
    if (state.failed) return { historyLine: "Runtime не отвечает", stateLine: "" };
    if (state.loading) return { historyLine: "Загрузка…", stateLine: "" };
    return { historyLine: "Событий ещё не было", stateLine: "Прогонов ещё не было" };
  }

  const latest = memory.events[0];
  const active = memory.runs.find((run) => run.status === "running" || run.status === "waiting");
  const run = active ?? memory.runs[0];
  return {
    historyLine: latest ? latest.eventType : "Событий ещё не было",
    stateLine: run ? `${runStatusWord(run.status)} · ${run.currentState}` : "Прогонов ещё не было",
  };
}
