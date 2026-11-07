import { describe, expect, it } from "vitest";
import { describeMemoryCard, formatMemoryValue } from "@/features/memory/utils/memoryCard";
import type { AgentMemoryEvent, AgentMemoryRun } from "@/features/runtime/types/runtime";

function event(eventType: string): AgentMemoryEvent {
  return {
    id: "e1",
    skillRunId: "run-1",
    skillId: "compose_letter",
    eventType,
    payload: {},
    fromState: null,
    toState: null,
    createdAt: "2026-10-12T11:00:00+00:00",
  };
}

function run(patch: Partial<AgentMemoryRun> = {}): AgentMemoryRun {
  return {
    skillRunId: "run-1",
    skillId: "compose_letter",
    status: "completed",
    currentState: "done",
    params: {},
    vars: {},
    conversationId: null,
    error: null,
    updatedAt: "2026-10-12T11:00:00+00:00",
    ...patch,
  };
}

describe("describeMemoryCard", () => {
  it("explains an empty agent", () => {
    expect(describeMemoryCard(null, { loading: false, failed: false })).toEqual({
      historyLine: "Событий ещё не было",
      stateLine: "Прогонов ещё не было",
    });
  });

  it("says when runtime is still loading or down", () => {
    expect(describeMemoryCard(null, { loading: true, failed: false }).historyLine).toBe("Загрузка…");
    expect(describeMemoryCard(null, { loading: false, failed: true }).historyLine).toBe(
      "Runtime не отвечает",
    );
  });

  it("prefers a live run over a finished one and names the latest event", () => {
    const lines = describeMemoryCard(
      {
        events: [event("channel.message.received")],
        runs: [
          run({ status: "completed", currentState: "done" }),
          run({ status: "waiting", currentState: "wait_review", skillRunId: "run-2" }),
        ],
      },
      { loading: false, failed: true },
    );

    expect(lines.historyLine).toBe("channel.message.received");
    expect(lines.stateLine).toBe("ждёт · wait_review");
  });

  it("mentions linked agents from the interaction manifesto", () => {
    const lines = describeMemoryCard(
      {
        events: [],
        runs: [],
        interaction: {
          version: 1,
          defaultAllowInbound: false,
          defaultAllowOutbound: false,
          peers: [{ agentSlug: "rt-a", allowInbound: true, allowOutbound: true }],
        },
      },
      { loading: false, failed: false },
    );
    expect(lines.stateLine).toBe("Связей: 1");
  });
});

describe("formatMemoryValue", () => {
  it("keeps empty and false values visible", () => {
    expect(formatMemoryValue(0)).toBe("0");
    expect(formatMemoryValue(false)).toBe("false");
    expect(formatMemoryValue("")).toBe("—");
    expect(formatMemoryValue(null)).toBe("—");
    expect(formatMemoryValue({ tone: "formal" })).toBe('{\n  "tone": "formal"\n}');
  });
});
