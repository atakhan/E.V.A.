import { describe, expect, it, beforeEach } from "vitest";
import type { Agent } from "@/features/agents/types/agent";
import { evaluateWorldLink } from "@/features/agents/utils/evaluateWorldLink";
import { createEmptySkill } from "@/features/skills/types/skill";
import { setToolCatalogForTests } from "@/features/tools/services/toolCatalogStore";
import type { ToolDefinition } from "@/features/tools/types/tool";

const telegramDef: ToolDefinition = {
  id: "telegram",
  name: "Telegram",
  description: "",
  world: true,
  commands: [{ id: "send_message", description: "" }],
  events: [{ id: "channel.message.received", description: "" }],
  states: [],
  credentialKind: "telegram_bot",
};

const webClientDef: ToolDefinition = {
  id: "web_client",
  name: "Web Client",
  description: "",
  world: true,
  commands: [{ id: "send_message", description: "" }],
  events: [{ id: "channel.message.received", description: "" }],
  states: [],
  credentialKind: "web_client",
};

const llmDef: ToolDefinition = {
  id: "llm",
  name: "LLM",
  description: "",
  world: false,
  commands: [{ id: "run", description: "" }],
  events: [],
  states: [],
};

function baseAgent(partial?: Partial<Agent>): Agent {
  return {
    id: "a1",
    slug: "test",
    name: "Test",
    description: "",
    icon: "",
    createdAt: "",
    updatedAt: "",
    skills: [],
    actions: [],
    tools: [],
    world: { addresses: [] },
    ...partial,
  };
}

describe("evaluateWorldLink", () => {
  beforeEach(() => {
    setToolCatalogForTests([telegramDef, webClientDef, llmDef]);
  });

  it("returns off for non-world tools", () => {
    const result = evaluateWorldLink(baseAgent(), "llm");
    expect(result.status).toBe("off");
  });

  it("returns off when kind is not connected", () => {
    expect(evaluateWorldLink(baseAgent(), "telegram").status).toBe("off");
  });

  it("returns red when connected without credential", () => {
    const agent = baseAgent({
      tools: [{ id: "tg1", toolId: "telegram", name: "TG", enabled: true, config: {} }],
    });
    expect(evaluateWorldLink(agent, "telegram").status).toBe("red");
  });

  it("returns yellow when credential ok but no behavior", () => {
    const agent = baseAgent({
      tools: [
        {
          id: "tg1",
          toolId: "telegram",
          name: "TG",
          enabled: true,
          credentialId: "cred-1",
          config: {},
        },
      ],
    });
    expect(evaluateWorldLink(agent, "telegram").status).toBe("yellow");
  });

  it("returns green when action uses the tool", () => {
    const agent = baseAgent({
      tools: [
        {
          id: "tg1",
          toolId: "telegram",
          name: "TG",
          enabled: true,
          credentialId: "cred-1",
          config: {},
        },
      ],
      actions: [
        {
          id: "reply",
          name: "Reply",
          description: "",
          version: "0.1.0",
          policy: "auto",
          inputSchema: {},
          outputSchema: {},
          recipe: [{ id: "s1", tool: "tg1", command: "send_message", input: {} }],
          createdAt: "",
          updatedAt: "",
        },
      ],
    });
    expect(evaluateWorldLink(agent, "telegram").status).toBe("green");
  });

  it("returns green when skill listens to tool event", () => {
    const agent = baseAgent({
      tools: [
        {
          id: "tg1",
          toolId: "telegram",
          name: "TG",
          enabled: true,
          credentialId: "cred-1",
          config: {},
        },
      ],
      skills: [
        {
          ...createEmptySkill({ id: "sk1", name: "Inbox" }),
          initial: "idle",
          states: [
            {
              id: "idle",
              name: "Idle",
              onEnter: [],
              final: false,
              transitions: [
                {
                  id: "t1",
                  event: "channel.message.received",
                  guard: "",
                  to: "idle",
                  actions: [],
                },
              ],
              x: 0,
              y: 0,
              width: 160,
              height: 80,
            },
          ],
        },
      ],
    });
    expect(evaluateWorldLink(agent, "telegram").status).toBe("green");
  });

  it("returns yellow for web client without an application even if a skill listens", () => {
    const agent = baseAgent({
      tools: [
        {
          id: "wc1",
          toolId: "web_client",
          name: "Web",
          enabled: true,
          credentialId: "old-channel-cred",
          config: {},
        },
      ],
      skills: [
        {
          ...createEmptySkill({ id: "sk1", name: "Inbox" }),
          initial: "idle",
          states: [
            {
              id: "idle",
              name: "Idle",
              onEnter: [],
              final: false,
              transitions: [
                {
                  id: "t1",
                  event: "channel.message.received",
                  guard: "",
                  to: "idle",
                  actions: [],
                },
              ],
              x: 0,
              y: 0,
              width: 160,
              height: 80,
            },
          ],
        },
      ],
    });
    expect(evaluateWorldLink(agent, "web_client").status).toBe("yellow");
    expect(evaluateWorldLink(agent, "web_client").reason).toBe("Нет подключённого приложения");
  });

  it("accepts address credential as red→yellow bridge", () => {
    const agent = baseAgent({
      tools: [{ id: "tg1", toolId: "telegram", name: "TG", enabled: true, config: {} }],
      world: {
        addresses: [
          { id: "addr1", toolId: "telegram", name: "Bot", credentialId: "cred-x" },
        ],
      },
    });
    expect(evaluateWorldLink(agent, "telegram").status).toBe("yellow");
  });
});
