import { describe, expect, it } from "vitest";
import type { Agent } from "@/features/agents/types/agent";
import type { ToolDefinition } from "@/features/tools/types/tool";
import { buildToolLibraryIndex } from "@/features/tools/utils/buildToolLibraryIndex";

const miniCatalog: ToolDefinition[] = [
  {
    id: "llm",
    name: "LLM",
    description: "",
    commands: [{ id: "run", description: "" }],
    events: [],
    states: [],
  },
  {
    id: "telegram",
    name: "Telegram",
    description: "",
    commands: [{ id: "send_message", description: "" }],
    events: [],
    states: [],
  },
  {
    id: "memory",
    name: "Memory",
    description: "",
    commands: [{ id: "search", description: "" }],
    events: [],
    states: [],
  },
];

function makeAgent(partial: Partial<Agent> & Pick<Agent, "id" | "slug" | "name">): Agent {
  return {
    description: "",
    createdAt: "",
    updatedAt: "",
    skills: [],
    actions: [],
    tools: [],
    ...partial,
  };
}

describe("buildToolLibraryIndex", () => {
  it("aggregates instances across agents and counts agents", () => {
    const agents: Agent[] = [
      makeAgent({
        id: "a1",
        slug: "alpha",
        name: "Alpha",
        tools: [
          { id: "llm", toolId: "llm", name: "LLM", enabled: true, config: {} },
          { id: "tg1", toolId: "telegram", name: "Bot A", enabled: true, config: {} },
        ],
      }),
      makeAgent({
        id: "a2",
        slug: "beta",
        name: "Beta",
        tools: [
          { id: "tg2", toolId: "telegram", name: "Bot B", enabled: false, config: {} },
        ],
      }),
    ];

    const index = buildToolLibraryIndex(agents, miniCatalog);
    const telegram = index.types.find((entry) => entry.definition.id === "telegram");
    const llm = index.types.find((entry) => entry.definition.id === "llm");
    const memory = index.types.find((entry) => entry.definition.id === "memory");

    expect(index.totalInstances).toBe(3);
    expect(telegram?.instances).toHaveLength(2);
    expect(telegram?.agentCount).toBe(2);
    expect(telegram?.enabledCount).toBe(1);
    expect(llm?.instances).toHaveLength(1);
    expect(memory?.instances).toHaveLength(0);
    expect(index.orphanInstances).toHaveLength(0);
  });

  it("includes catalog types without instances", () => {
    const index = buildToolLibraryIndex([], miniCatalog);
    expect(index.types).toHaveLength(3);
    expect(index.types.every((entry) => entry.instances.length === 0)).toBe(true);
    expect(index.totalInstances).toBe(0);
  });

  it("collects orphan instances for unknown tool ids", () => {
    const agents: Agent[] = [
      makeAgent({
        id: "a1",
        slug: "alpha",
        name: "Alpha",
        tools: [
          { id: "custom1", toolId: "unknown_tool", name: "Custom", enabled: true, config: {} },
        ],
      }),
    ];

    const index = buildToolLibraryIndex(agents, miniCatalog);
    expect(index.orphanInstances).toHaveLength(1);
    expect(index.orphanInstances[0]?.instance.id).toBe("custom1");
    expect(index.totalInstances).toBe(1);
  });

  it("sorts types with instances before empty ones", () => {
    const agents: Agent[] = [
      makeAgent({
        id: "a1",
        slug: "alpha",
        name: "Alpha",
        tools: [{ id: "llm", toolId: "llm", name: "LLM", enabled: true, config: {} }],
      }),
    ];

    const index = buildToolLibraryIndex(agents, miniCatalog);
    expect(index.types[0]?.definition.id).toBe("llm");
    expect(index.types.slice(1).every((entry) => entry.instances.length === 0)).toBe(true);
  });

  it("sorts usage rows by agent name then instance name", () => {
    const agents: Agent[] = [
      makeAgent({
        id: "a2",
        slug: "beta",
        name: "Beta",
        tools: [{ id: "tg2", toolId: "telegram", name: "Z Bot", enabled: true, config: {} }],
      }),
      makeAgent({
        id: "a1",
        slug: "alpha",
        name: "Alpha",
        tools: [{ id: "tg1", toolId: "telegram", name: "A Bot", enabled: true, config: {} }],
      }),
    ];

    const index = buildToolLibraryIndex(agents, miniCatalog);
    const telegram = index.types.find((entry) => entry.definition.id === "telegram");
    expect(telegram?.instances.map((row) => row.agentName)).toEqual(["Alpha", "Beta"]);
  });
});
